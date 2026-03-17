import ijson
import os
import sys
import django
from pathlib import Path

# Ajoute le dossier parent au PATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enron_project.settings')
django.setup()

from investigation.models import Person, Email, Recipient
from datetime import datetime

def stream_import(file_path):
    """Importe les emails en streaming avec ijson"""
    
    base_dir = Path(__file__).resolve().parent.parent
    full_path = base_dir / file_path
    
    print(f"🚀 Début de l'import streaming depuis {full_path}")
    
    # Cache pour les personnes
    person_cache = {}
    
    with open(full_path, 'r', encoding='utf-16') as f:
        # 'item' correspond à chaque objet du tableau JSON
        objects = ijson.items(f, 'item')
        
        count = 0
        skipped = 0
        
        for entry in objects:
            try:
                # Ne garde que les emails
                if entry.get('model') != 'investigation.email':
                    continue
                
                fields = entry.get('fields', {})
                
                # Gère l'expéditeur
                from_email = fields.get('from_person')
                if not from_email:
                    skipped += 1
                    continue
                
                # Nettoie l'email
                if isinstance(from_email, dict) and 'email' in from_email:
                    from_email = from_email['email']
                
                # Récupère ou crée la personne
                if from_email not in person_cache:
                    person, _ = Person.objects.get_or_create(
                        email=from_email,
                        defaults={'name': ''}
                    )
                    person_cache[from_email] = person
                
                # Gère la date
                date_str = fields.get('date')
                if date_str:
                    try:
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        date = None
                else:
                    date = None
                
                # Crée l'email
                email = Email.objects.create(
                    message_id=fields.get('message_id', f"import_{count}"),
                    from_person=person_cache[from_email],
                    subject=fields.get('subject', '')[:255],
                    body=fields.get('body', ''),
                    date=date or datetime.now(),
                    folder=fields.get('folder', ''),
                )
                
                count += 1
                
                if count % 1000 == 0:
                    print(f"✅ {count} emails importés...")
                    
            except Exception as e:
                print(f"❌ Erreur sur un objet: {e}")
                skipped += 1
    
    print("\n" + "="*50)
    print("📊 RÉSUMÉ DE L'IMPORT")
    print("="*50)
    print(f"✅ Emails importés : {count}")
    print(f"⚠️  Objets ignorés : {skipped}")
    print(f"👥 Personnes en cache : {len(person_cache)}")

if __name__ == "__main__":
    stream_import('data_final.json')