from django.db import models


class Queue(models.Model):
    SERVICE_TYPES = [
        ('GUICHET_AEROPORT', 'Guichet Aéroport'),
        ('GUICHET_SOA_TRANS', 'Guichet Soa Trans'),
        ('MANITRA_PLUS', 'Manitra Plus'),
        ('BNI_MADAGASCAR', 'BNI Madagascar'),
        ('BFV', 'BFV'),
        ('MICRO_FINANCE', 'Micro-finance'),
        ('INSTITUT_PASTEUR', 'Institut Pasteur'),
        ('CHU', 'CHU'),
        ('ADMINISTRATIF', 'Administratif'),
        ('SERVICE_CLIENT_MULTICANAL', 'Service client multicanal'),
        ('GUICHET_ADMINISTRATIF', 'Guichet administratif'),
        ('SUPPORT_TECHNIQUE', 'Support technique (ticketing)'),
        ('DRIVE_RESTAURANT', 'Drive de restaurant'),
        ('HOPITAL_URGENCES', 'Hôpital – Urgences'),
        ('CENTRE_VACCINATION', 'Centre de vaccination'),
    ]

    name = models.CharField(max_length=100, unique=True)
    service_type = models.CharField(
        max_length=50,
        choices=SERVICE_TYPES,
        default='GUICHET_AEROPORT',
        verbose_name='Département / type de guichet'
    )
    max_capacity = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.get_service_type_display()}"

    @property
    def department_label(self):
        return self.name or self.get_service_type_display()


class Agent(models.Model):
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('busy', 'Occupé'),
        ('break', 'Pause'),
        ('offline', 'Hors ligne'),
    ]

    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, related_name='agents')
    name = models.CharField(max_length=100)
    agent_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    current_ticket = models.ForeignKey('QueueItem', null=True, blank=True, on_delete=models.SET_NULL, related_name='served_by')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['agent_number']
        unique_together = ['queue', 'agent_number']

    def __str__(self):
        return f"Guichet {self.agent_number} - {self.queue.name}"


class QueueItem(models.Model):
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, related_name='items')
    position = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    served = models.BooleanField(default=False)
    served_at = models.DateTimeField(null=True, blank=True)
    assigned_agent = models.ForeignKey('Agent', null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_tickets')

    class Meta:
        ordering = ['position']
        unique_together = ['queue', 'position']

    def __str__(self):
        return f"Ticket {self.position} - {self.queue.name}"

    @property
    def status(self):
        return 'Appelé' if self.served else 'En attente'

    @property
    def status_css(self):
        return 'success' if self.served else 'warning'
