from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Queue, Agent

def agents_list(request, queue_id):
    queue = get_object_or_404(Queue, id=queue_id, is_active=True)
    agents = queue.agents.filter(is_active=True)
    return render(request, 'queueapp/agents_list.html', {
        'queue': queue,
        'agents': agents,
    })

def get_agents_data(request, queue_id):
    queue = get_object_or_404(Queue, id=queue_id)
    agents = queue.agents.filter(is_active=True).values('id', 'name', 'agent_number', 'status', 'current_ticket_id')
    return JsonResponse({
        'agents': list(agents),
    })

def call_next_agent(request, queue_id, agent_id):
    if request.method == 'POST':
        queue = get_object_or_404(Queue, id=queue_id)
        agent = get_object_or_404(Agent, id=agent_id, queue=queue)
        item = queue.items.filter(served=False).order_by('position').first()
        
        if item:
            item.served = True
            item.save()
            
            agent.current_ticket = item
            agent.status = 'busy'
            agent.save()
            
            return JsonResponse({
                'status': 'ok',
                'position': item.position,
                'agent': agent.name,
            })
        return JsonResponse({'status': 'empty'})
    return JsonResponse({'status': 'error'})

def update_agent_status(request, agent_id):
    if request.method == 'POST':
        agent = get_object_or_404(Agent, id=agent_id)
        new_status = request.POST.get('status', 'available')
        
        if new_status in dict(Agent.STATUS_CHOICES):
            agent.status = new_status
            if new_status == 'available':
                agent.current_ticket = None
            agent.save()
            return JsonResponse({
                'status': 'ok',
                'agent_status': agent.status,
            })
        return JsonResponse({'status': 'error', 'message': 'Statut invalide'})
    return JsonResponse({'status': 'error'})
