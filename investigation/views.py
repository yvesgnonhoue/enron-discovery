from django.shortcuts import render, get_object_or_404
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.db import models
from .models import Email, Person
import re

def dashboard(request):
    # Statistiques globales
    total_emails = Email.objects.count()
    total_persons = Person.objects.count()
    
    # Filtre les dates valides (entre 1998 et 2003)
    valid_emails = Email.objects.filter(
        date__year__gte=1998,
        date__year__lte=2003
    )
    
    # Dates extrêmes
    first_date = valid_emails.order_by('date').first()
    last_date = valid_emails.order_by('-date').first()
    
    # Volume par mois (uniquement dates valides)
    monthly_counts = valid_emails.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Top 10 expéditeurs
    top_senders = Person.objects.annotate(
        count=Count('sent_emails')
    ).order_by('-count')[:10]
    
    context = {
        'total_emails': total_emails,
        'total_persons': total_persons,
        'first_date': first_date.date if first_date else None,
        'last_date': last_date.date if last_date else None,
        'monthly_counts': monthly_counts,
        'top_senders': top_senders,
    }
    return render(request, 'investigation/dashboard.html', context)


def search(request):
    """Page de recherche optimisée pour PostgreSQL avec select_related"""
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    sender_id = request.GET.get('sender', '')
    
    # Personnes pour le filtre
    persons = Person.objects.filter(
        email__icontains='@enron.com'
    ).exclude(
        email__startswith=('.', '"', "'", '#', '!')
    ).order_by('email')[:100]
    
    # BASE DE REQUÊTE AVEC SELECT_RELATED POUR POSTGRESQL
    emails = Email.objects.all().select_related('from_person')
    
    # Application des filtres
    if date_from:
        emails = emails.filter(date__gte=date_from)
    if date_to:
        emails = emails.filter(date__lte=date_to)
    if sender_id and sender_id.isdigit():
        emails = emails.filter(from_person_id=sender_id)
    if query:
        emails = emails.filter(
            models.Q(subject__icontains=query) |
            models.Q(body__icontains=query)
        )
    
    # Résultats limités (les from_person sont déjà chargés)
    results = emails[:100]
    
    # Gestion sécurisée de l'expéditeur sélectionné
    selected_sender = ''
    if sender_id and sender_id.isdigit():
        selected_sender = int(sender_id)
    
    context = {
        'results': results,
        'query': query,
        'date_from': date_from,
        'date_to': date_to,
        'selected_sender': selected_sender,
        'persons': persons,
    }
    return render(request, 'investigation/search.html', context)


def thread(request, email_id):
    """Affiche un email et toutes ses réponses (optimisé PostgreSQL)"""
    email = get_object_or_404(
        Email.objects.select_related('from_person'), 
        id=email_id
    )
    
    # Fonction pour récupérer toutes les réponses récursivement
    def get_replies(msg):
        replies = Email.objects.filter(
            in_reply_to=msg
        ).select_related('from_person').order_by('date')
        result = []
        for reply in replies:
            result.append(reply)
            result.extend(get_replies(reply))
        return result
    
    # Récupère le fil complet
    thread_messages = [email] + get_replies(email)
    
    context = {
        'thread': thread_messages,
        'root_email': email,
    }
    return render(request, 'investigation/thread.html', context)