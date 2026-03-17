"""
SCRIPT D'IMPORT DES EMAILS ENRON
Rôle : Parcourir tous les fichiers .eml et les insérer dans la base Django
"""

import os
import sys
import django
import email
from datetime import datetime
from pathlib import Path
from email.utils import parsedate_to_datetime

# Configuration pour utiliser Django depuis un script externe
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enron_project.settings')
django.setup()

# Après django.setup(), on peut importer les modèles
from investigation.models import Person, Email, Recipient

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data' / 'maildir'

print(f"📁 Dossier des données : {DATA_DIR}")

def parse_email_file(file_path, folder_name):
    """
    Lit un fichier .eml et extrait les informations
    Retourne un dictionnaire avec les données ou None si erreur
    """
    try:
        # Ouvre le fichier en ignorant les erreurs d'encodage
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            msg = email.message_from_file(f)
        
        # Extraction des champs principaux
        message_id = msg.get('Message-ID', '').strip('<>')
        from_addr = clean_email(msg.get('From', ''))
        to_addrs = parse_addresses(msg.get('To', ''))
        cc_addrs = parse_addresses(msg.get('Cc', ''))
        subject = msg.get('Subject', '')[:255]  # Limite la longueur
        date_str = msg.get('Date', '')
        in_reply_to = msg.get('In-Reply-To', '').strip('<>')
        
        # Extraction du corps du message
        body = get_body(msg) #récupère le texte brut de l'email
        body = clean_signatures(body) #nettoie les signatures
        
        # Conversion de la date
        date = None
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except:
                date = None
        
        return {
            'message_id': message_id or f"unknown_{file_path.name}",
            'from': from_addr,
            'to': to_addrs,
            'cc': cc_addrs,
            'subject': subject,
            'body': body,
            'date': date,
            'in_reply_to': in_reply_to or None,
            'folder': folder_name,
            'file_path': str(file_path)
        }
    except Exception as e:
        print(f"❌ Erreur sur {file_path.name}: {e}")
        return None

def clean_email(email_str):
    """Nettoie une adresse email (enlève les < > et normalise)"""
    if not email_str:
        return None
    # Extrait ce qui est entre < >
    import re
    match = re.search(r'<(.+?)>', email_str)
    if match:
        return match.group(1).lower()
    # Sinon retourne la chaîne nettoyée
    return email_str.lower().strip()

def parse_addresses(addr_str):
    """Convertit une chaîne d'adresses en liste"""
    if not addr_str:
        return []
    addrs = []
    for part in addr_str.split(','):
        clean = clean_email(part)
        if clean:
            addrs.append(clean)
    return addrs

def get_body(msg):
    """Extrait le corps du message (partie texte)"""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                try:
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    return ""
    else:
        try:
            return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            return ""
    return ""

def import_emails():
    """Fonction principale d'import"""
    print("🚀 Début de l'import des emails...")
    
    if not DATA_DIR.exists():
        print(f"❌ Dossier introuvable : {DATA_DIR}")
        return
    
    # Compteurs
    total_files = 0
    imported = 0
    skipped = 0
    
    # Dictionnaire pour cache des personnes (évite de recréer)
    person_cache = {}
    
    # Parcours de l'arborescence
    for person_dir in DATA_DIR.iterdir():
        if not person_dir.is_dir():
            continue
            
        print(f"\n📁 Traitement de : {person_dir.name}")
        
        for folder in person_dir.iterdir():
            if not folder.is_dir():
                continue
                
            folder_name = f"{person_dir.name}/{folder.name}"
            
            for email_file in folder.iterdir():
                total_files += 1
                
                if total_files % 1000 == 0:
                    print(f"⏳ {total_files} fichiers traités...")
                
                # Parse le fichier
                data = parse_email_file(email_file, folder_name)
                if not data:
                    skipped += 1
                    continue
                
                try:
                    # 1. Gérer l'expéditeur
                    from_email = data['from']
                    if not from_email:
                        from_email = 'unknown@enron.com'
                    
                    if from_email not in person_cache:
                        person, _ = Person.objects.get_or_create(
                            email=from_email,
                            defaults={'name': ''}
                        )
                        person_cache[from_email] = person
                    
                    # 2. Créer l'email
                    email_obj = Email.objects.create(
                        message_id=data['message_id'],
                        from_person=person_cache[from_email],
                        subject=data['subject'],
                        body=data['body'],
                        date=data['date'] or datetime.now(),
                        folder=data['folder']
                    )
                    
                    # 3. Gérer les destinataires (To)
                    for to_addr in data['to']:
                        if to_addr not in person_cache:
                            person, _ = Person.objects.get_or_create(
                                email=to_addr,
                                defaults={'name': ''}
                            )
                            person_cache[to_addr] = person
                        
                        Recipient.objects.create(
                            email=email_obj,
                            person=person_cache[to_addr],
                            type='to'
                        )
                    
                    # 4. Gérer les destinataires (Cc)
                    for cc_addr in data['cc']:
                        if cc_addr not in person_cache:
                            person, _ = Person.objects.get_or_create(
                                email=cc_addr,
                                defaults={'name': ''}
                            )
                            person_cache[cc_addr] = person
                        
                        Recipient.objects.create(
                            email=email_obj,
                            person=person_cache[cc_addr],
                            type='cc'
                        )
                    
                    imported += 1
                    
                except Exception as e:
                    print(f"❌ Erreur insertion {email_file.name}: {e}")
                    skipped += 1
    
    print("\n" + "="*50)
    print("📊 RÉSUMÉ DE L'IMPORT")
    print("="*50)
    print(f"📁 Fichiers trouvés : {total_files}")
    print(f"✅ Emails importés : {imported}")
    print(f"⚠️  Fichiers ignorés : {skipped}")
    print(f"👥 Personnes uniques : {len(person_cache)}")

def clean_signatures(body):
    """Supprime les signatures courantes des emails"""
    if not body:
        return body
    
    # Liste des motifs de signature à supprimer
    signature_patterns = [
        r'\n--\n.*$',  # Signature avec --
        r'\n__+\n.*$',  # Signature avec ___
        r'\n-+\n.*$',   # Signature avec ---
        r'\nConfidential.*$',
        r'\nPrivileged.*$',
        r'\nThis message contains.*$',
    ]
    
    import re
    for pattern in signature_patterns:
        body = re.sub(pattern, '', body, flags=re.DOTALL | re.IGNORECASE)
    
    return body.strip()

if __name__ == "__main__":
    import_emails()