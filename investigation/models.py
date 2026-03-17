from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
class Person(models.Model):
    """Un employé/acteur d'Enron (expéditeur ou destinataire)"""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return self.email

class Email(models.Model):
    """Un message email"""
    message_id = models.CharField(max_length=255, unique=True)
    from_person = models.ForeignKey(
        Person, 
        on_delete=models.CASCADE, 
        related_name='sent_emails'
    )
    subject = models.TextField(blank=True)
    body = models.TextField()
    date = models.DateTimeField()
    in_reply_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    folder = models.CharField(max_length=255, blank=True)
    search_vector = SearchVectorField(null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['from_person']),
            GinIndex(fields=['search_vector']),
        ]
    
    def __str__(self):
        return f"{self.subject[:50]} - {self.date}"

class Recipient(models.Model):
    """Relation entre un email et ses destinataires"""
    class RecipientType(models.TextChoices):
        TO = 'to', 'To'
        CC = 'cc', 'Cc'
        BCC = 'bcc', 'Bcc'
    
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='recipients')
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    type = models.CharField(max_length=3, choices=RecipientType.choices)
    
    class Meta:
        unique_together = ['email', 'person', 'type']
        indexes = [
            models.Index(fields=['email', 'person']),
        ]
    
    def __str__(self):
        return f"{self.person.email} ({self.type})"