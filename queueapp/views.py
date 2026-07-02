from functools import wraps
from io import BytesIO
import csv
import os
import re

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db import models, transaction, IntegrityError
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect, resolve_url
from django.utils import timezone

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .models import Queue, QueueItem, Agent


User = get_user_model()


def _reset_application_runtime_data():
    """Remet à zéro les données opérationnelles sans supprimer les départements."""
    with transaction.atomic():
        QueueItem.objects.all().delete()
        Agent.objects.update(status='available', current_ticket=None)


def login_user(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('index')

    context = {
        'mode': 'login',
        'next': request.POST.get('next') or request.GET.get('next') or '',
    }

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        context['login_username'] = username

        user = authenticate(request, username=username, password=password)
        if user is None:
            context['login_error'] = 'Identifiant ou mot de passe incorrect. Veuillez réessayer.'
            return render(request, 'queueapp/login.html', context)

        if not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=['is_staff', 'is_superuser'])

        auth_login(request, user)
        next_url = context.get('next')
        return redirect(next_url or 'index')

    return render(request, 'queueapp/login.html', context)


def register_user(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('index')

    context = {'mode': 'register'}

    if request.method == 'POST':
        full_name = (request.POST.get('full_name') or '').strip()
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        password_confirm = request.POST.get('password_confirm') or ''

        context.update({
            'register_full_name': full_name,
            'register_username': username,
            'register_email': email,
        })

        if len(username) < 3:
            context['register_error'] = 'Le nom d’utilisateur doit contenir au moins 3 caractères.'
            return render(request, 'queueapp/login.html', context)

        if len(password) < 4:
            context['register_error'] = 'Le mot de passe doit contenir au moins 4 caractères.'
            return render(request, 'queueapp/login.html', context)

        if password != password_confirm:
            context['register_error'] = 'Les deux mots de passe ne correspondent pas.'
            return render(request, 'queueapp/login.html', context)

        if User.objects.filter(username__iexact=username).exists():
            context['register_error'] = 'Ce nom d’utilisateur existe déjà. Choisissez un autre nom.'
            return render(request, 'queueapp/login.html', context)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name,
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=['is_staff', 'is_superuser'])

        _reset_application_runtime_data()
        auth_login(request, user)
        return redirect('index')

    return render(request, 'queueapp/login.html', context)


def superuser_required(view_func):
    """Réserve une vue aux super-utilisateurs Django."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), resolve_url(settings.LOGIN_URL))

        if not request.user.is_superuser:
            wants_json = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest'
                or request.path.endswith('/data/')
                or request.method == 'POST'
            )
            if wants_json:
                return JsonResponse({
                    'status': 'forbidden',
                    'message': 'Accès refusé : seul le super-utilisateur peut consulter ou modifier ces données.'
                }, status=403)
            return render(request, 'queueapp/403_superuser.html', status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def _queue_icon(service_type):
    mapping = {
        'Guichet Aéroport': 'plane-departure',
        'Guichet Soa Trans': 'bus',
        'Manitra Plus': 'store',
        'BNI Madagascar': 'university',
        'BFV': 'landmark',
        'Micro-finance': 'hand-holding-usd',
        'Institut Pasteur': 'microscope',
        'CHU': 'hospital',
        'Administratif': 'file-signature',
        'Service client multicanal': 'headset',
        'Guichet administratif': 'building',
        'Support technique (ticketing)': 'tools',
        'Drive de restaurant': 'utensils',
        'Hôpital – Urgences': 'ambulance',
        'Centre de vaccination': 'syringe',
    }
    return mapping.get(service_type, 'users')


def _queue_logo(service_type):
    """Logo local de secours pour chaque département."""
    mapping = {
        'Guichet Aéroport': 'queueapp/img/departments/air-madagascar.png',
        'Guichet Soa Trans': 'queueapp/img/departments/soa-trans.svg',
        'Manitra Plus': 'queueapp/img/departments/manitra-plus.svg',
        'BNI Madagascar': 'queueapp/img/departments/bni-madagascar.svg',
        'BFV': 'queueapp/img/departments/bfv.svg',
        'Micro-finance': 'queueapp/img/departments/micro-finance.svg',
        'Institut Pasteur': 'queueapp/img/departments/institut-pasteur.svg',
        'CHU': 'queueapp/img/departments/chu.svg',
        'Administratif': 'queueapp/img/departments/administratif.svg',
        'Centre de vaccination': 'queueapp/img/departments/centre-vaccination.svg',
    }
    return mapping.get(service_type, 'queueapp/img/departments/default.svg')


def _queue_logo_url(service_type):
    """Logos fournis par le propriétaire du projet.

    Les URLs sont utilisées sans changer la logique métier. Le logo local reste
    disponible comme secours dans les templates si une image distante ne charge
    pas.
    """
    mapping = {
        'Guichet Aéroport': 'https://i.postimg.cc/HsFd01WW/photo-2026-06-20-03-58-00.jpg',
        'Guichet Soa Trans': 'https://i.postimg.cc/RV241xCS/photo-2026-06-20-03-58-02.jpg',
        'Manitra Plus': 'https://i.postimg.cc/Pr0TbnfH/photo-2026-06-20-03-57-53.jpg',
        'BNI Madagascar': 'https://i.postimg.cc/NfZB8vGj/photo-2026-06-20-03-58-05.jpg',
        'BFV': 'https://i.postimg.cc/pTdLGQw2/photo-2026-06-20-04-13-49.jpg',
        'Micro-finance': 'https://i.postimg.cc/7Yjw1rPf/photo-2026-06-20-04-02-23.jpg',
        'Institut Pasteur': 'https://i.postimg.cc/QxvhgZNj/photo-2026-06-20-03-57-57.jpg',
        'CHU': 'https://i.postimg.cc/SNHkLbQs/photo-2026-06-20-04-02-19.jpg',
        'Administratif': 'https://i.postimg.cc/qMW4cHBg/photo-2026-06-20-04-02-21.jpg',
        'Centre de vaccination': 'https://i.postimg.cc/QxvhgZNj/photo-2026-06-20-03-57-57.jpg',
    }
    return mapping.get(service_type, '')


def _queue_showcase(service_type):
    """Visuels d’accueil propres à chaque département.

    Ces données servent uniquement à l’affichage du diaporama. Elles ne
    changent pas la logique des tickets, des guichets ou des appels.
    """
    mapping = {
        'Administratif': {
            'eyebrow': 'Accueil administratif',
            'title': 'Administratif : accès aux documents officiels et services publics.',
            'description': 'Régulation des accès aux services de délivrance de documents officiels, comme CIN, passeport et copies certifiées. Solution antibouchon pour l’administration publique.',
            'slides': [
                'https://i.postimg.cc/7L860xpp/photo-2026-06-20-09-51-05.jpg',
                'https://i.postimg.cc/KYSzBZ6v/photo-2026-06-20-03-58-12.jpg',
            ],
        },
        'BFV': {
            'eyebrow': 'Accueil bancaire BFV',
            'title': 'BFV-SG : accueil bancaire, caisse et rendez-vous conseillers.',
            'description': 'Régulation de l’accueil, des opérations de caisse et des rendez-vous conseillers. Prise en charge dédiée pour les comptes Privilège et Entreprise.',
            'slides': [
                'https://i.postimg.cc/yN4dcVMV/photo-2026-06-20-09-51-09.jpg',
                'https://i.postimg.cc/25R6hzsf/photo-2026-06-20-09-51-10.jpg',
            ],
        },
        'BNI Madagascar': {
            'eyebrow': 'Accueil BNI Madagascar',
            'title': 'Une présentation BNI Madagascar pour gérer les tickets et les guichets.',
            'description': 'Les usagers retrouvent un accueil lié à la BNI Madagascar, avec un service clair, structuré et adapté aux opérations bancaires.',
            'slides': [
                'https://i.postimg.cc/7L3LNF4w/photo-2026-06-20-09-51-12.jpg',
                'https://i.postimg.cc/1zhtw9k3/photo-2026-06-20-09-51-20.jpg',
                'https://i.postimg.cc/PqWqMgHr/photo-2026-06-20-09-51-22.jpg',
            ],
        },
        'CHU': {
            'eyebrow': 'Accueil hospitalier CHU',
            'title': 'Une page adaptée au cadre hospitalier et à l’orientation des patients.',
            'description': 'Le CHU dispose d’un fond d’accueil lié à son environnement afin de rendre la page plus humaine, plus claire et plus cohérente avec le service de santé.',
            'slides': [
                'https://i.postimg.cc/CKGK4300/photo-2026-06-20-09-51-26.jpg',
                'https://i.postimg.cc/LstsVcS8/photo-2026-06-20-09-51-31.jpg',
                'https://i.postimg.cc/MG7GYCwc/photo-2026-06-20-09-51-35.jpg',
                'https://i.postimg.cc/6QrQhkK4/photo-2026-06-20-09-51-33.jpg',
            ],
        },
        'Guichet Soa Trans': {
            'eyebrow': 'Accueil Soa Trans',
            'title': 'Un habillage lié au transport pour mieux situer le service.',
            'description': 'Pilotage des flux pour le service fret, l’envoi, la réception et la réservation des voyageurs. Filtrage personnalisé par ligne de transport ou type de colis.',
            'slides': [
                'https://i.postimg.cc/CKGK430B/photo-2026-06-20-09-51-37.jpg',
                'https://i.postimg.cc/TPVPczxD/photo-2026-06-20-09-51-41.jpg',
            ],
        },
        'Institut Pasteur': {
            'eyebrow': 'Accueil Institut Pasteur',
            'title': 'Institut Pasteur de Madagascar : laboratoire, vaccination et résultats.',
            'description': 'La page de l’Institut Pasteur illustre l’accueil des visiteurs, l’organisation du service et le suivi des demandes dans un cadre professionnel.',
            'slides': [
                'https://i.postimg.cc/mrYrSv4Q/photo-2026-06-20-09-51-44.jpg',
                'https://i.postimg.cc/VNqNFxwM/photo-2026-06-20-09-51-43.jpg',
                'https://i.postimg.cc/9fdfB62t/photo-2026-06-20-09-51-46.jpg',
            ],
        },
        'Manitra Plus': {
            'eyebrow': 'Accueil Manitra Plus',
            'title': 'Une ambiance propre à Manitra Plus pour valoriser l’accueil client.',
            'description': 'Le service Manitra Plus utilise ses propres images pour créer une page d’accueil harmonieuse, facile à reconnaître et agréable à utiliser.',
            'slides': [
                'https://i.postimg.cc/QMQMq2Dq/photo-2026-06-20-09-51-48.jpg',
                'https://i.postimg.cc/rp1p9BTN/photo-2026-06-20-09-51-47.jpg',
            ],
        },
        'Micro-finance': {
            'eyebrow': 'Accueil micro-finance',
            'title': 'Une présentation liée à la micro-finance pour mieux guider les clients.',
            'description': 'Le département micro-finance affiche un diaporama qui rappelle l’accompagnement, les demandes de financement et le suivi des clients.',
            'slides': [
                'https://i.postimg.cc/cJRJcpWm/photo-2026-06-20-09-51-49-(2).jpg',
                'https://i.postimg.cc/TwT3Nt2W/photo-2026-06-20-09-51-49.jpg',
            ],
        },
        'Guichet Aéroport': {
            'eyebrow': 'Accueil aéroportuaire',
            'title': 'Un accueil inspiré du secteur aérien pour orienter les passagers.',
            'description': 'Le guichet aéroport met en avant l’univers du voyage et l’orientation des passagers, tout en gardant la gestion des tickets déjà opérationnelle.',
            'slides': [
                'https://i.postimg.cc/HsFd01WW/photo-2026-06-20-03-58-00.jpg',
            ],
        },
    }
    default = {
        'eyebrow': 'Accueil du département',
        'title': 'Un espace de supervision clair et professionnel.',
        'description': 'Chaque département garde sa logique de gestion tout en bénéficiant d’un visuel d’accueil dédié pour rendre la page plus claire et plus agréable.',
        'slides': ['https://i.postimg.cc/KYSzBZ6v/photo-2026-06-20-03-58-12.jpg'],
    }
    payload = mapping.get(service_type, default).copy()
    payload['service_type'] = service_type
    return payload


def _queue_summary(queue):
    pending_qs = queue.items.filter(served=False)
    served_qs = queue.items.filter(served=True)
    available_agents = queue.agents.filter(is_active=True, status='available').count()
    busy_agents = queue.agents.filter(is_active=True, status='busy').count()
    active_agents = queue.agents.filter(is_active=True).count()
    current_count = pending_qs.count()
    capacity_rate = round((current_count / queue.max_capacity) * 100, 1) if queue.max_capacity else 0
    service_type = queue.get_service_type_display()
    return {
        'id': queue.id,
        'name': queue.name,
        'department': queue.name,
        'service_type': service_type,
        'icon': _queue_icon(service_type),
        'logo': _queue_logo(service_type),
        'logo_url': _queue_logo_url(service_type),
        'max_capacity': queue.max_capacity,
        'current_count': current_count,
        'served_count': served_qs.count(),
        'available_agents': available_agents,
        'busy_agents': busy_agents,
        'active_agents': active_agents,
        'capacity_rate': capacity_rate,
        'status_label': 'Complet' if current_count >= queue.max_capacity else 'Ouvert',
        'updated_at': timezone.now().isoformat(),
    }


def _pdf_safe(value):
    """Nettoie les caractères difficiles pour les polices PDF standards."""
    value = str(value or '')
    replacements = {
        '’': "'",
        '‘': "'",
        '“': '"',
        '”': '"',
        '–': '-',
        '—': '-',
        'œ': 'oe',
        'Œ': 'OE',
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value


def _ticket_public_number(ticket):
    """Numéro court affiché sur le ticket professionnel."""
    service = ticket.queue.get_service_type_display()
    prefixes = {
        'Administratif': 'A',
        'BFV': 'B',
        'BNI Madagascar': 'N',
        'CHU': 'C',
        'Guichet Aéroport': 'AIR',
        'Guichet Soa Trans': 'S',
        'Institut Pasteur': 'P',
        'Manitra Plus': 'M',
        'Micro-finance': 'F',
    }
    prefix = prefixes.get(service, re.sub(r'[^A-Z]', '', service.upper())[:2] or 'T')
    return f'{prefix}{ticket.position:03d}'


def _ticket_department_mention(ticket):
    service = ticket.queue.get_service_type_display()
    mentions = {
        'Guichet Aéroport': 'Billetterie et relation clientèle',
        'BFV': 'Accueil bancaire et opérations de caisse',
        'BNI Madagascar': 'Guichet bancaire et services clients',
        'Guichet Soa Trans': 'Réservation, fret et accueil voyageurs',
        'Manitra Plus': 'Comptoir de vente et encaissement',
        'Micro-finance': 'Dépôts, retraits et microcrédits',
        'Administratif': 'Documents officiels et service public',
        'Institut Pasteur': 'Laboratoire, vaccination et résultats',
        'CHU': 'Accueil, triage et consultations',
    }
    return mentions.get(service, f'Service {service}')


def _ticket_code(ticket):
    safe_queue = re.sub(r'[^A-Z0-9]', '', ticket.queue.name.upper())[:4] or 'MQ'
    return f'{safe_queue}-{ticket.position:03d}-{ticket.id}'


def _ticket_people_ahead(ticket):
    if ticket.served:
        return 0
    return ticket.queue.items.filter(served=False, position__lt=ticket.position).count()


def _ticket_payload(request, ticket):
    url = request.build_absolute_uri(f'/ticket/{ticket.id}/')
    created = timezone.localtime(ticket.created_at)
    return {
        'ticket_id': ticket.id,
        'ticket_code': _ticket_code(ticket),
        'public_number': _ticket_public_number(ticket),
        'position': ticket.position,
        'department': ticket.queue.name,
        'service': ticket.queue.get_service_type_display(),
        'department_mention': _ticket_department_mention(ticket),
        'created_at': created.strftime('%d/%m/%Y %H:%M'),
        'created_date': created.strftime('%d/%m/%Y'),
        'created_time': created.strftime('%Hh %Mmin'),
        'people_ahead': _ticket_people_ahead(ticket),
        'status': ticket.status,
        'url': url,
    }


def _draw_centered_text(pdf, text, x, y, font='Helvetica', size=10, color=colors.black):
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    pdf.drawCentredString(x, y, _pdf_safe(text))


def _draw_ticket_logo(pdf, x, y, size):
    """Dessine le logo de l'application si disponible, sinon un pictogramme simple."""
    logo_path = os.path.join(settings.BASE_DIR, 'queueapp', 'static', 'queueapp', 'img', 'logo-files-attente.png')
    if os.path.exists(logo_path):
        try:
            pdf.drawImage(ImageReader(logo_path), x, y, width=size, height=size, preserveAspectRatio=True, mask='auto')
            return
        except Exception:
            pass

    pdf.setFillColor(colors.HexColor('#0b63bd'))
    pdf.circle(x + size / 2, y + size / 2, size / 2, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.circle(x + size / 2, y + size / 2, size * 0.34, stroke=0, fill=1)
    pdf.setFillColor(colors.HexColor('#0b63bd'))
    pdf.circle(x + size / 2, y + size * 0.45, size * 0.13, stroke=0, fill=1)
    pdf.roundRect(x + size * 0.37, y + size * 0.18, size * 0.26, size * 0.22, size * 0.08, stroke=0, fill=1)


def _draw_cutout_ticket(pdf, card_x, card_y, card_w, card_h, bg_color):
    """Fond de ticket avec bordures façon ticket détachable."""
    for offset, alpha_color in [
        (4 * mm, '#d8dde7'),
        (2.5 * mm, '#e3e7ee'),
        (1.2 * mm, '#edf0f5'),
    ]:
        pdf.setFillColor(colors.HexColor(alpha_color))
        pdf.roundRect(card_x + offset, card_y - offset, card_w, card_h, 3 * mm, stroke=0, fill=1)

    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(colors.HexColor('#d3d7df'))
    pdf.setLineWidth(0.45)
    pdf.roundRect(card_x, card_y, card_w, card_h, 2.8 * mm, stroke=1, fill=1)

    # Perforations sur les quatre bords.
    pdf.setFillColor(bg_color)
    r = 1.8 * mm
    step = 5.4 * mm
    x = card_x + 4 * mm
    while x < card_x + card_w - 4 * mm:
        pdf.circle(x, card_y + card_h + r * 0.18, r, stroke=0, fill=1)
        pdf.circle(x, card_y - r * 0.18, r, stroke=0, fill=1)
        x += step

    y = card_y + 4 * mm
    while y < card_y + card_h - 4 * mm:
        pdf.circle(card_x - r * 0.18, y, r, stroke=0, fill=1)
        pdf.circle(card_x + card_w + r * 0.18, y, r, stroke=0, fill=1)
        y += step

    # Découpes rondes latérales, comme un ticket de service.
    pdf.circle(card_x, card_y + card_h / 2, 11 * mm, stroke=0, fill=1)
    pdf.circle(card_x + card_w, card_y + card_h / 2, 11 * mm, stroke=0, fill=1)


def _generate_ticket_pdf(request, ticket):
    payload = _ticket_payload(request, ticket)
    width, height = 210 * mm, 140 * mm
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    pdf.setTitle(f"Ticket {payload['public_number']} - {payload['department']}")

    bg_color = colors.HexColor('#f4f6f9')
    pdf.setFillColor(bg_color)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    card_w = 164 * mm
    card_h = 94 * mm
    card_x = (width - card_w) / 2
    card_y = (height - card_h) / 2
    _draw_cutout_ticket(pdf, card_x, card_y, card_w, card_h, bg_color)

    left = card_x + 18 * mm
    right = card_x + card_w - 18 * mm
    center = card_x + card_w / 2
    top = card_y + card_h

    # En-tête du ticket.
    logo_size = 28 * mm
    _draw_ticket_logo(pdf, left, top - 35 * mm, logo_size)

    pdf.setFillColor(colors.HexColor('#2b2f36'))
    pdf.setFont('Helvetica-Bold', 22)
    pdf.drawString(left + 43 * mm, top - 21 * mm, _pdf_safe('Bienvenue'))
    pdf.setFont('Helvetica', 17)
    pdf.drawString(left + 43 * mm, top - 32 * mm, _pdf_safe("au Service d'Accueil"))

    pdf.setStrokeColor(colors.HexColor('#525252'))
    pdf.setLineWidth(0.7)
    pdf.line(left, top - 40 * mm, right, top - 40 * mm)

    # Numéro principal.
    _draw_centered_text(pdf, 'NUMERO', center, top - 50 * mm, 'Helvetica', 15, colors.HexColor('#777777'))
    _draw_centered_text(pdf, payload['public_number'], center, top - 72 * mm, 'Helvetica-Bold', 45, colors.HexColor('#2b2b2b'))

    pdf.setStrokeColor(colors.HexColor('#777777'))
    pdf.setLineWidth(0.55)
    pdf.line(left + 10 * mm, top - 77 * mm, right - 10 * mm, top - 77 * mm)

    # Département et mention spécifique.
    _draw_centered_text(pdf, f"Departement : {payload['department']}", center, top - 88 * mm, 'Helvetica-Bold', 15.5, colors.HexColor('#303030'))
    _draw_centered_text(pdf, payload['department_mention'], center, top - 96 * mm, 'Helvetica', 9.5, colors.HexColor('#545454'))

    pdf.setStrokeColor(colors.HexColor('#a4a4a4'))
    pdf.setLineWidth(0.45)
    pdf.line(left + 10 * mm, top - 101 * mm, right - 10 * mm, top - 101 * mm)

    # Date, heure et code de suivi.
    info_x = left + 28 * mm
    pdf.setFillColor(colors.HexColor('#333333'))
    pdf.setFont('Helvetica', 13.5)
    pdf.drawString(info_x, top - 112 * mm, _pdf_safe(f"Date : {payload['created_date']}"))
    pdf.drawString(info_x, top - 123 * mm, _pdf_safe(f"Heure : {payload['created_time']}"))

    pdf.setFont('Helvetica', 8.5)
    pdf.setFillColor(colors.HexColor('#6b7280'))
    pdf.drawRightString(right - 28 * mm, top - 112 * mm, _pdf_safe(f"Code : {payload['ticket_code']}"))
    pdf.drawRightString(right - 28 * mm, top - 123 * mm, _pdf_safe(f"Devant vous : {payload['people_ahead']}"))

    pdf.setStrokeColor(colors.HexColor('#b6b6b6'))
    pdf.line(left + 10 * mm, top - 130 * mm, right - 10 * mm, top - 130 * mm)

    _draw_centered_text(pdf, "Veuillez patienter s'il vous plait...", center, top - 139 * mm, 'Helvetica-Oblique', 13, colors.HexColor('#4b4b4b'))

    # Mention du projet, discrète pour ne pas alourdir le ticket.
    _draw_centered_text(pdf, 'IS Info | DSI | ISALOSYS Sarl Madagascar', center, card_y + 5 * mm, 'Helvetica', 6.8, colors.HexColor('#9ca3af'))

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


@superuser_required
def index(request):
    queues = list(Queue.objects.filter(is_active=True).order_by('name'))
    queue_cards = [_queue_summary(queue) for queue in queues]
    total_capacity = sum(queue.max_capacity for queue in queues)
    total_waiting = sum(card['current_count'] for card in queue_cards)
    total_served = sum(card['served_count'] for card in queue_cards)
    total_agents = sum(card['active_agents'] for card in queue_cards)
    available_agents = sum(card['available_agents'] for card in queue_cards)
    busy_agents = sum(card['busy_agents'] for card in queue_cards)
    saturation_rate = round((total_waiting / total_capacity) * 100, 1) if total_capacity else 0

    return render(request, 'queueapp/index.html', {
        'queues': queues,
        'queue_cards': queue_cards,
        'total_capacity': total_capacity,
        'total_waiting': total_waiting,
        'total_served': total_served,
        'total_agents': total_agents,
        'available_agents': available_agents,
        'busy_agents': busy_agents,
        'saturation_rate': saturation_rate,
    })


@superuser_required
def queue_detail(request, queue_id):
    queue = get_object_or_404(Queue, id=queue_id, is_active=True)
    pending_items = queue.items.filter(served=False).order_by('position')
    served_items = queue.items.filter(served=True).order_by('-served_at', '-created_at')[:10]
    all_queues = Queue.objects.filter(is_active=True).order_by('name')
    queue_summaries = [_queue_summary(item) for item in all_queues]
    return render(request, 'queueapp/queue_detail.html', {
        'queue': queue,
        'pending_items': pending_items,
        'served_items': served_items,
        'queue_summaries': queue_summaries,
        'queue_logo': _queue_logo(queue.get_service_type_display()),
        'queue_logo_url': _queue_logo_url(queue.get_service_type_display()),
        'queue_showcase': _queue_showcase(queue.get_service_type_display()),
    })


@superuser_required
def call_board(request, queue_id):
    queue = get_object_or_404(Queue, id=queue_id, is_active=True)
    return render(request, 'queueapp/call_board.html', {
        'queue': queue,
        'queue_summary': _queue_summary(queue),
        'queue_logo': _queue_logo(queue.get_service_type_display()),
        'queue_logo_url': _queue_logo_url(queue.get_service_type_display()),
    })


@superuser_required
def add_to_queue(request, queue_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

    with transaction.atomic():
        queue = get_object_or_404(Queue.objects.select_for_update(), id=queue_id, is_active=True)
        pending_count = queue.items.filter(served=False).count()
        if pending_count >= queue.max_capacity:
            return JsonResponse({'status': 'full', 'message': 'La file est complète'})

        last_position = queue.items.aggregate(max_pos=models.Max('position'))['max_pos'] or 0
        new_pos = last_position + 1
        item = QueueItem.objects.create(queue=queue, position=new_pos)

    return JsonResponse({
        'status': 'ok',
        'message': 'Ticket créé avec succès',
        'position': new_pos,
        'ticket_id': item.id,
        'ticket_code': _ticket_code(item),
        'people_ahead': _ticket_people_ahead(item),
        'ticket_url': request.build_absolute_uri(f'/ticket/{item.id}/'),
        'ticket_pdf_url': request.build_absolute_uri(f'/ticket/{item.id}/pdf/'),
        'department': queue.name,
        'service': queue.get_service_type_display(),
        'summary': _queue_summary(queue),
    })


@superuser_required
def next_in_queue(request, queue_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

    with transaction.atomic():
        queue = get_object_or_404(Queue.objects.select_for_update(), id=queue_id, is_active=True)
        agent = queue.agents.select_for_update().filter(
            is_active=True,
            status='available'
        ).order_by('agent_number').first()

        if not agent:
            return JsonResponse({
                'status': 'no_agent',
                'message': 'Impossible d’appeler un ticket : aucun agent n’est disponible.',
                'summary': _queue_summary(queue),
            })

        item = queue.items.select_for_update().filter(served=False).order_by('position').first()
        if not item:
            return JsonResponse({'status': 'empty', 'message': 'Aucun client en attente'})

        called_position = item.position
        item.served = True
        item.served_at = timezone.now()
        item.assigned_agent = agent
        item.save(update_fields=['served', 'served_at', 'assigned_agent'])

        agent.current_ticket = item
        agent.status = 'busy'
        agent.save(update_fields=['current_ticket', 'status'])

        remaining = queue.items.filter(served=False).order_by('position')
        next_item = remaining.first()

    return JsonResponse({
        'status': 'ok',
        'message': f'Ticket {called_position} appelé et affecté à {agent.name} - guichet {agent.agent_number}',
        'position': called_position,
        'ticket_id': item.id,
        'agent': agent.name,
        'agent_number': agent.agent_number,
        'department': queue.name,
        'service': queue.get_service_type_display(),
        'remaining_count': remaining.count(),
        'next_position': next_item.position if next_item else None,
        'summary': _queue_summary(queue),
    })


@superuser_required
def get_queue_data(request, queue_id):
    queue = get_object_or_404(Queue, id=queue_id, is_active=True)
    pending_items = list(queue.items.filter(served=False).order_by('position').values('id', 'position', 'created_at', 'served'))
    served_items = list(queue.items.filter(served=True).select_related('assigned_agent').order_by('-served_at', '-created_at').values('id', 'position', 'created_at', 'served', 'served_at', 'assigned_agent__name', 'assigned_agent__agent_number')[:10])
    data = _queue_summary(queue)
    data.update({
        'pending_items': pending_items,
        'served_items': served_items,
    })
    return JsonResponse(data)


@superuser_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(QueueItem.objects.select_related('queue', 'assigned_agent'), id=ticket_id)
    queue = ticket.queue
    return render(request, 'queueapp/ticket_detail.html', {
        'ticket': ticket,
        'queue': queue,
        'ticket_code': _ticket_code(ticket),
        'ticket_public_number': _ticket_public_number(ticket),
        'ticket_department_mention': _ticket_department_mention(ticket),
        'people_ahead': _ticket_people_ahead(ticket),
        'queue_logo': _queue_logo(queue.get_service_type_display()),
        'queue_logo_url': _queue_logo_url(queue.get_service_type_display()),
    })


@superuser_required
def ticket_pdf(request, ticket_id):
    ticket = get_object_or_404(QueueItem.objects.select_related('queue', 'assigned_agent'), id=ticket_id)
    pdf_buffer = _generate_ticket_pdf(request, ticket)
    filename = f'ticket_{_ticket_code(ticket)}.pdf'
    pdf_content = pdf_buffer.getvalue()
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    # Autorise l'aperçu du PDF dans l'iframe de la page courante.
    # Sans cette ligne, Django peut envoyer X-Frame-Options: DENY,
    # ce qui provoque la zone grise avec l'icône de fichier cassé.
    response['X-Frame-Options'] = 'SAMEORIGIN'
    response['Cache-Control'] = 'no-store, max-age=0'
    response['Content-Length'] = str(len(pdf_content))
    return response


@superuser_required
def agents_list(request, queue_id):
    queue = get_object_or_404(Queue, id=queue_id, is_active=True)
    agents = queue.agents.filter(is_active=True).order_by('agent_number')
    return render(request, 'queueapp/agents_list.html', {
        'queue': queue,
        'agents': agents,
        'queue_logo': _queue_logo(queue.get_service_type_display()),
        'queue_logo_url': _queue_logo_url(queue.get_service_type_display()),
    })


@superuser_required
def get_agents_data(request, queue_id):
    queue = get_object_or_404(Queue, id=queue_id, is_active=True)
    agents = queue.agents.filter(is_active=True).order_by('agent_number').values(
        'id', 'name', 'agent_number', 'status', 'current_ticket_id', 'current_ticket__position'
    )
    return JsonResponse({'agents': list(agents)})


@superuser_required
def call_next_agent(request, queue_id, agent_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

    with transaction.atomic():
        queue = get_object_or_404(Queue.objects.select_for_update(), id=queue_id, is_active=True)
        agent = get_object_or_404(Agent.objects.select_for_update(), id=agent_id, queue=queue, is_active=True)

        if agent.status != 'available':
            return JsonResponse({'status': 'unavailable', 'message': 'Cet agent n’est pas disponible'})

        item = queue.items.select_for_update().filter(served=False).order_by('position').first()
        if not item:
            return JsonResponse({'status': 'empty', 'message': 'Aucun ticket en attente'})

        item.served = True
        item.served_at = timezone.now()
        item.assigned_agent = agent
        item.save(update_fields=['served', 'served_at', 'assigned_agent'])
        agent.current_ticket = item
        agent.status = 'busy'
        agent.save(update_fields=['current_ticket', 'status'])

    return JsonResponse({
        'status': 'ok',
        'message': f'Ticket {item.position} assigné à {agent.name}',
        'position': item.position,
        'ticket_id': item.id,
        'agent': agent.name,
        'agent_number': agent.agent_number,
        'department': queue.name,
        'service_type': queue.get_service_type_display(),
        'summary': _queue_summary(queue),
    })


@superuser_required
def update_agent_status(request, agent_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

    agent = get_object_or_404(Agent, id=agent_id, is_active=True)
    new_status = request.POST.get('status', 'available')

    if new_status not in dict(Agent.STATUS_CHOICES):
        return JsonResponse({'status': 'error', 'message': 'Statut invalide'})

    agent.status = new_status
    if new_status in ['available', 'break', 'offline']:
        agent.current_ticket = None
    agent.save(update_fields=['status', 'current_ticket'])
    return JsonResponse({
        'status': 'ok',
        'message': f'Statut mis à jour : {agent.get_status_display()}',
        'agent_status': agent.status,
    })


def _parse_agent_number(value):
    try:
        number = int(value)
        if number <= 0:
            raise ValueError
        return number
    except (TypeError, ValueError):
        return None


@superuser_required
def add_agent(request, queue_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

    queue = get_object_or_404(Queue, id=queue_id, is_active=True)
    agent_number = _parse_agent_number(request.POST.get('agent_number'))
    name = (request.POST.get('name') or '').strip()

    if not agent_number or not name:
        return JsonResponse({'status': 'error', 'message': 'Veuillez renseigner un numéro de guichet valide et le nom de l’agent'})

    existing = Agent.objects.filter(queue=queue, agent_number=agent_number).first()
    if existing and existing.is_active:
        return JsonResponse({'status': 'error', 'message': 'Ce numéro de guichet existe déjà pour cette file'})

    if existing and not existing.is_active:
        existing.name = name
        existing.status = 'available'
        existing.current_ticket = None
        existing.is_active = True
        existing.save(update_fields=['name', 'status', 'current_ticket', 'is_active'])
        agent = existing
    else:
        try:
            agent = Agent.objects.create(queue=queue, agent_number=agent_number, name=name)
        except IntegrityError:
            return JsonResponse({'status': 'error', 'message': 'Ce numéro de guichet existe déjà pour cette file'})

    return JsonResponse({
        'status': 'ok',
        'agent_id': agent.id,
        'message': f'Agent {name} créé avec succès'
    })


@superuser_required
def edit_agent(request, agent_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

    agent = get_object_or_404(Agent.objects.select_related('queue'), id=agent_id, is_active=True)
    agent_number = _parse_agent_number(request.POST.get('agent_number'))
    name = (request.POST.get('name') or '').strip()
    status = (request.POST.get('status') or agent.status).strip()

    if not agent_number or not name:
        return JsonResponse({'status': 'error', 'message': 'Veuillez renseigner un numéro de guichet valide et le nom de l’agent'})

    if status not in dict(Agent.STATUS_CHOICES):
        return JsonResponse({'status': 'error', 'message': 'Statut invalide'})

    if Agent.objects.filter(queue=agent.queue, agent_number=agent_number).exclude(id=agent.id).exists():
        return JsonResponse({'status': 'error', 'message': 'Ce numéro de guichet existe déjà pour cette file'})

    agent.name = name
    agent.agent_number = agent_number
    agent.status = status
    if status in ['available', 'break', 'offline']:
        agent.current_ticket = None
    agent.save(update_fields=['name', 'agent_number', 'status', 'current_ticket'])

    return JsonResponse({
        'status': 'ok',
        'message': f'Agent {agent.name} modifié avec succès',
        'agent': {
            'id': agent.id,
            'name': agent.name,
            'agent_number': agent.agent_number,
            'status': agent.status,
        }
    })


@superuser_required
def delete_agent(request, agent_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

    agent = get_object_or_404(Agent.objects.select_related('queue'), id=agent_id, is_active=True)
    name = agent.name
    number = agent.agent_number

    # Suppression logique pour conserver l'historique des tickets déjà appelés.
    agent.current_ticket = None
    agent.status = 'offline'
    agent.is_active = False
    agent.save(update_fields=['current_ticket', 'status', 'is_active'])

    return JsonResponse({
        'status': 'ok',
        'message': f'Guichet {number} - {name} supprimé avec succès'
    })


@superuser_required
def auto_distribute_tasks(request, queue_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

    with transaction.atomic():
        queue = get_object_or_404(Queue.objects.select_for_update(), id=queue_id, is_active=True)
        available_agents = list(queue.agents.select_for_update().filter(is_active=True, status='available').order_by('agent_number'))
        pending_items = list(queue.items.select_for_update().filter(served=False).order_by('position')[:len(available_agents)])

        if not available_agents:
            return JsonResponse({'status': 'empty_agents', 'message': 'Aucun agent disponible', 'assigned_count': 0})
        if not pending_items:
            return JsonResponse({'status': 'empty_queue', 'message': 'Aucun ticket en attente', 'assigned_count': 0})

        assignments = []
        for agent, item in zip(available_agents, pending_items):
            item.served = True
            item.served_at = timezone.now()
            item.assigned_agent = agent
            item.save(update_fields=['served', 'served_at', 'assigned_agent'])
            agent.current_ticket = item
            agent.status = 'busy'
            agent.save(update_fields=['current_ticket', 'status'])
            assignments.append({
                'agent': agent.name,
                'agent_number': agent.agent_number,
                'position': item.position,
                'ticket_id': item.id,
                'department': queue.name,
            })

    return JsonResponse({
        'status': 'ok',
        'message': f'{len(assignments)} ticket(s) assigné(s) automatiquement',
        'assigned_count': len(assignments),
        'assignments': assignments,
        'department': queue.name,
        'service_type': queue.get_service_type_display(),
        'summary': _queue_summary(queue),
    })


@superuser_required
def auto_distribute_info(request, queue_id):
    queue = get_object_or_404(Queue, id=queue_id, is_active=True)
    available_agents = queue.agents.filter(is_active=True, status='available').count()
    pending_items = queue.items.filter(served=False).count()

    return JsonResponse({
        'available_agents': available_agents,
        'pending_items': pending_items,
        'can_distribute': available_agents > 0 and pending_items > 0
    })


@superuser_required
def tickets_export_page(request):
    queues = Queue.objects.filter(is_active=True).order_by('name')
    selected_queue_id = request.GET.get('queue')
    selected_status = request.GET.get('status', 'all')

    tickets = QueueItem.objects.select_related('queue', 'assigned_agent').filter(queue__is_active=True)
    selected_queue = None
    if selected_queue_id:
        selected_queue = get_object_or_404(Queue, id=selected_queue_id, is_active=True)
        tickets = tickets.filter(queue=selected_queue)

    if selected_status == 'pending':
        tickets = tickets.filter(served=False)
    elif selected_status == 'served':
        tickets = tickets.filter(served=True)

    waiting_count = tickets.filter(served=False).count()
    served_count = tickets.filter(served=True).count()
    total_count = tickets.count()
    recent_tickets = tickets.order_by('-served_at', '-created_at')[:100]

    return render(request, 'queueapp/exports.html', {
        'queues': queues,
        'tickets': recent_tickets,
        'selected_queue': selected_queue,
        'selected_queue_id': selected_queue_id or '',
        'selected_status': selected_status,
        'waiting_count': waiting_count,
        'served_count': served_count,
        'total_count': total_count,
    })


@superuser_required
def export_tickets_csv(request):
    selected_queue_id = request.GET.get('queue')
    selected_status = request.GET.get('status', 'all')

    tickets = QueueItem.objects.select_related('queue', 'assigned_agent').filter(queue__is_active=True)
    filename = 'tickets_multiqueue.csv'

    if selected_queue_id:
        queue = get_object_or_404(Queue, id=selected_queue_id, is_active=True)
        tickets = tickets.filter(queue=queue)
        safe_name = ''.join(ch for ch in queue.name.lower().replace(' ', '_') if ch.isalnum() or ch in ['_', '-'])
        filename = f'tickets_{safe_name}.csv'

    if selected_status == 'pending':
        tickets = tickets.filter(served=False)
        filename = filename.replace('.csv', '_en_attente.csv')
    elif selected_status == 'served':
        tickets = tickets.filter(served=True)
        filename = filename.replace('.csv', '_traites.csv')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'ID ticket', 'Code ticket', 'Département', 'File', 'Type de service', 'Position', 'Statut',
        'Agent affecté', 'Guichet', 'Personnes devant', 'Date de création', 'Heure de création',
        'Date de traitement', 'Heure de traitement'
    ])
    for ticket in tickets.order_by('queue__name', 'position'):
        local_created = timezone.localtime(ticket.created_at)
        local_served = timezone.localtime(ticket.served_at) if ticket.served_at else None
        writer.writerow([
            ticket.id,
            _ticket_code(ticket),
            ticket.queue.name,
            ticket.queue.name,
            ticket.queue.get_service_type_display(),
            ticket.position,
            'Traité' if ticket.served else 'En attente',
            ticket.assigned_agent.name if ticket.assigned_agent else '',
            ticket.assigned_agent.agent_number if ticket.assigned_agent else '',
            _ticket_people_ahead(ticket),
            local_created.strftime('%d/%m/%Y'),
            local_created.strftime('%H:%M:%S'),
            local_served.strftime('%d/%m/%Y') if local_served else '',
            local_served.strftime('%H:%M:%S') if local_served else '',
        ])
    return response


@login_required
def logout_user(request):
    if request.user.is_superuser:
        _reset_application_runtime_data()
    logout(request)
    return redirect('login')
