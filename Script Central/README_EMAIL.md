# Configuration de l'envoi par email

Le script peut maintenant envoyer automatiquement le rapport Excel généré par email.

## Configuration

Pour activer l'envoi par email, ajoutez les paramètres suivants dans le fichier `.env` de chaque client (dans le dossier `.env/`).

### Paramètres requis

```env
# Serveur SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Destinataire(s)
EMAIL_TO=destinataire@example.com
EMAIL_FROM=votre_email@gmail.com

# Authentification (si nécessaire)
SMTP_USERNAME=votre_email@gmail.com
SMTP_PASSWORD=votre_mot_de_passe
```

### Paramètres optionnels

```env
# Copie carbone (plusieurs adresses séparées par des virgules)
EMAIL_CC=cc1@example.com,cc2@example.com

# Sujet personnalisé (par défaut : "Rapport Aruba Central - {nom_client}")
EMAIL_SUBJECT=Rapport mensuel Aruba Central - {nom_client}
```

## Exemple de configuration complète

Voici un exemple de fichier `.env` complet avec la configuration email :

```env
# Configuration Aruba Central
CLIENT_ID=votre_client_id
CLIENT_SECRET=votre_client_secret
CUSTOMER_ID=votre_customer_id
CENTRAL_USERNAME=votre_username
CENTRAL_PASSWORD=votre_password
BASE_URL=https://apigw-eucentral3.central.arubanetworks.com

# Configuration Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=votre_email@gmail.com
SMTP_PASSWORD=votre_mot_de_passe_app
EMAIL_FROM=votre_email@gmail.com
EMAIL_TO=destinataire@example.com
EMAIL_CC=manager@example.com
EMAIL_SUBJECT=Rapport Aruba Central - {nom_client}
```

## Configuration pour différents fournisseurs email

### Gmail

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=votre_email@gmail.com
SMTP_PASSWORD=votre_mot_de_passe_app  # Utilisez un mot de passe d'application, pas votre mot de passe Gmail
EMAIL_FROM=votre_email@gmail.com
```

**Important pour Gmail** : Vous devez utiliser un [mot de passe d'application](https://support.google.com/accounts/answer/185833) plutôt que votre mot de passe Gmail standard.

### Outlook / Office 365

```env
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=votre_email@outlook.com
SMTP_PASSWORD=votre_mot_de_passe
EMAIL_FROM=votre_email@outlook.com
```

### Serveur SMTP personnalisé

```env
SMTP_SERVER=smtp.votre-domaine.com
SMTP_PORT=587  # ou 465 pour SSL, 25 pour non sécurisé
SMTP_USERNAME=votre_utilisateur
SMTP_PASSWORD=votre_mot_de_passe
EMAIL_FROM=noreply@votre-domaine.com
```

## Fonctionnement

1. **Si la configuration email est présente** : Le script envoie automatiquement le rapport Excel par email après sa génération.

2. **Si la configuration email est absente** : Le script continue normalement et sauvegarde uniquement le fichier localement.

3. **Gestion des erreurs** : Si l'envoi d'email échoue, le script affiche un message d'erreur mais ne bloque pas l'exécution.

## Sécurité

⚠️ **Important** : Les fichiers `.env` contiennent des informations sensibles (mots de passe, clés API). 

- Ne commitez **jamais** ces fichiers dans un dépôt Git
- Assurez-vous que le fichier `.gitignore` exclut le dossier `.env/`
- Utilisez des mots de passe d'application plutôt que des mots de passe principaux quand c'est possible

## Test

Pour tester la configuration email, exécutez simplement le script :

```bash
python "Script Central/main.py"
```

Si la configuration email est correcte, vous verrez :
```
✅ Rapport Excel généré : D:\Aruba-Central-API-Report\Script Central\Report\Client1.xlsx
📧 Configuration email détectée, envoi du rapport...
📧 Connexion au serveur SMTP : smtp.gmail.com:587
✅ Email envoyé avec succès à : destinataire@example.com
```

Si la configuration email est absente ou incorrecte, vous verrez :
```
✅ Rapport Excel généré : D:\Aruba-Central-API-Report\Script Central\Report\Client1.xlsx
ℹ️  Aucune configuration email trouvée. Le rapport a été sauvegardé localement.
```

## Dépannage

### Erreur d'authentification

- Vérifiez que `SMTP_USERNAME` et `SMTP_PASSWORD` sont corrects
- Pour Gmail, utilisez un mot de passe d'application
- Vérifiez que l'authentification à deux facteurs est configurée correctement

### Erreur de connexion

- Vérifiez que `SMTP_SERVER` et `SMTP_PORT` sont corrects
- Vérifiez votre connexion Internet
- Vérifiez que le pare-feu/autorise les connexions SMTP sortantes

### Email non reçu

- Vérifiez le dossier spam/courrier indésirable
- Vérifiez que `EMAIL_TO` est correct
- Vérifiez les logs du script pour voir si l'email a été envoyé avec succès

