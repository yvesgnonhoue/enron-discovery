from django.shortcuts import render, get_object_or_404
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.db import models
from django.http import JsonResponse
from .models import Email, Person
import re

def dashboard(request):
    # Récupère les filtres de date
    start_date = request.GET.get('start_date', '1998-01-01')
    end_date = request.GET.get('end_date', '2002-12-31')
    
    emails = Email.objects.all()
    if start_date:
        emails = emails.filter(date__gte=start_date)
    if end_date:
        emails = emails.filter(date__lte=end_date)
    
    total_emails = emails.count()
    total_persons = Person.objects.filter(sent_emails__in=emails).distinct().count()
    
    first_date = emails.order_by('date').first()
    last_date = emails.order_by('-date').first()
    
    monthly_counts = emails.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    top_senders = Person.objects.filter(
        sent_emails__in=emails
    ).annotate(
        count=Count('sent_emails')
    ).order_by('-count')[:10]
    
    all_years = Email.objects.dates('date', 'year')
    
    context = {
        'total_emails': total_emails,
        'total_persons': total_persons,
        'first_date': first_date.date if first_date else None,
        'last_date': last_date.date if last_date else None,
        'monthly_counts': monthly_counts,
        'top_senders': top_senders,
        'all_years': all_years,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'investigation/dashboard.html', context)


def search(request):
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    sender_id = request.GET.get('sender', '')
    
    persons = Person.objects.filter(
        email__icontains='@enron.com'
    ).exclude(
        email__startswith=('.', '"', "'", '#', '!')
    ).order_by('email')[:100]
    
    emails = Email.objects.all().select_related('from_person')
    
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
    
    results = emails[:100]
    
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
    email = get_object_or_404(
        Email.objects.select_related('from_person'), 
        id=email_id
    )
    
    def get_replies(msg):
        replies = Email.objects.filter(
            in_reply_to=msg
        ).select_related('from_person').order_by('date')
        result = []
        for reply in replies:
            result.append(reply)
            result.extend(get_replies(reply))
        return result
    
    thread_messages = [email] + get_replies(email)
    
    context = {
        'thread': thread_messages,
        'root_email': email,
    }
    return render(request, 'investigation/thread.html', context)


def suggest_email_subjects(request):
    """API d'autocomplétion pour sujets et expéditeurs"""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)

    # Sujets
    subjects = Email.objects.filter(
        subject__icontains=q
    ).exclude(
        subject__isnull=True
    ).exclude(
        subject=''
    ).values_list('subject', flat=True).distinct()[:10]

    # Expéditeurs
    senders = Email.objects.filter(
        from_person__email__icontains=q
    ).values_list('from_person__email', flat=True).distinct()[:5]

    results = []
    for s in subjects:
        label = f"📧 Sujet : {s[:80]}…" if len(s) > 80 else f"📧 Sujet : {s}"
        results.append({'value': s, 'label': label})

    for s in senders:
        results.append({'value': s, 'label': f"✉️ Expéditeur : {s}"})

    results = results[:12]
    return JsonResponse(results, safe=False)