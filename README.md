# 🎯 Telegram Job & Internship Alert Bot (LinkedIn + Gemini AI + GitHub Actions)

[![GitHub Actions](https://img.shields.io/badge/Automated%20with-GitHub%20Actions-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Python 3.12](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Telegram Bot](https://img.shields.io/badge/Notification-Telegram-26A5E4?logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)
[![Google Gemini](https://img.shields.io/badge/AI%20Summary-Google%20Gemini%202.5-8E75B2?logo=googlegemini&logoColor=white)](https://aistudio.google.com/)

Une application **100 % gratuite et sans serveur à héberger** qui scanne quotidiennement les nouvelles offres d'emploi ou de stage sur LinkedIn, les résume intelligemment avec **Google Gemini AI**, filtre les doublons, et vous les envoie chaque matin sur **Telegram** — **même lorsque votre ordinateur est éteint**.

---

## ✨ Fonctionnalités

- 🤖 **100 % Cloud & Gratuit** : Tourne automatiquement tous les matins grâce à **GitHub Actions** (aucune carte bancaire ni serveur payant requis).
- 🧠 **Résumé IA avec Google Gemini** : Lit la description complète de chaque offre et génère un résumé de 4-5 lignes (missions, compétences/stack, durée et dates).
- 🔁 **Zéro Doublon (`seen_jobs.json`)** : Le workflow mémorise automatiquement les offres déjà envoyées dans le dépôt GitHub pour ne vous envoyer que les vraies nouveautés.
- 🛠️ **Applicable à toutes les professions** : Personnalisable en 30 secondes via un simple fichier [`search_config.json`](./search_config.json) (Ingénieur IA/Data, Architecte, Développeur, Finance, Marketing, en Stage, Alternance, CDI ou Freelance).

---

## 🏗️ Architecture

```text
[GitHub Actions (Tous les matins à 08h/09h)]
       │
       ▼
[cloud_bot.py] ──(1)──► Lit vos critères dans search_config.json
       │
       ├──(2)──► Scanne les nouvelles offres LinkedIn correspondantes
       │
       ├──(3)──► Filtre les offres déjà vues (seen_jobs.json)
       │
       ├──(4)──► Résume la fiche de poste avec Google Gemini 2.5 Flash
       │
       ├──(5)──► Envoie l'alerte formatée sur votre téléphone via Telegram
       │
       └──(6)──► Sauvegarde automatiquement seen_jobs.json sur votre dépôt GitHub
```

---

## 🚀 Tutoriel Complet d'Installation (5 minutes)

### Étape 1 : Copier ce projet sur votre compte GitHub (Fork)
1. Cliquez sur le bouton **Fork** en haut à droite de cette page GitHub pour créer votre propre copie du projet.
2. *(Optionnel)* Si vous avez des offres déjà dans [`seen_jobs.json`](./seen_jobs.json), vous pouvez vider la liste `"seen_job_ids": []` pour repartir de zéro.

---

### Étape 2 : Créer votre Bot Telegram et récupérer vos 2 clés (`TOKEN` & `CHAT_ID`)

#### A. Obtenir votre `TELEGRAM_BOT_TOKEN`
1. Ouvrez Telegram et lancez une discussion avec le robot officiel **[@BotFather](https://t.me/BotFather)** (badge bleu vérifié).
2. Envoyez la commande :
   ```text
   /newbot
   ```
3. Donnez un **nom d'affichage** à votre bot (ex. `Mon Alerte Emploi`).
4. Choisissez un **identifiant unique** qui se termine obligatoirement par `bot` (ex. `prenom_jobs_2026_bot`).
5. **BotFather** vous génère un jeton secret sous **"Use this token to access the HTTP API:"** de la forme :
   ```text
   1234567890:AAH_exempleDeTokenSecret123456789
   ```
   👉 C'est votre **`TELEGRAM_BOT_TOKEN`**.
6. **⚠️ Important** : Cliquez sur le lien `t.me/votre_bot` donné par BotFather, appuyez sur **Démarrer** (**Start**) et envoyez-lui un premier message (ex. `Bonjour`).

#### B. Obtenir votre `TELEGRAM_CHAT_ID`
Après avoir envoyé `Bonjour` à votre bot, ouvrez cet URL dans votre navigateur en remplaçant `<VOTRE_TOKEN>` par votre token :
```text
https://api.telegram.org/bot<VOTRE_TOKEN>/getUpdates
```
Cherchez dans le texte affiché la section `"chat":{"id":123456789,...}`.
👉 Ce numéro (ex. `123456789`) est votre **`TELEGRAM_CHAT_ID`**.

*(Alternative : vous pouvez aussi lancer localement `python send_telegram.py` après avoir mis votre token dans un fichier local `config.json`, il détectera et affichera votre `chat_id` automatiquement !)*

---

### Étape 3 : Obtenir votre clé gratuite Google Gemini (`GEMINI_API_KEY`)
1. Rendez-vous sur **[Google AI Studio](https://aistudio.google.com/apikey)** et connectez-vous avec votre compte Google.
2. Cliquez sur **Create API key**.
3. Copiez la clé générée (qui commence par `AIzaSy...`).
   👉 C'est votre **`GEMINI_API_KEY`** *(100 % gratuite avec le modèle `gemini-2.5-flash`)*.

> 💡 *Note : Cette clé est optionnelle. Si vous ne la mettez pas, le bot fonctionnera quand même et vous enverra les 700 premiers caractères de la description de l'offre.*

---

### Étape 4 : Ajouter vos clés dans les Secrets GitHub
Vos clés ne doivent **jamais** être écrites dans le code public. Elles se rangent dans le coffre-fort sécurisé de GitHub :

1. Sur votre dépôt GitHub, cliquez sur l'onglet **Settings** (en haut).
2. Dans le menu de gauche, cliquez sur **Secrets and variables** ➔ **Actions**.
3. Cliquez sur le bouton vert **New repository secret** et ajoutez ces **3 secrets** un par un :

| Name (Nom exact du secret) | Secret (Valeur à coller) |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Le token donné par `@BotFather` (ex. `123456:AAH...`) |
| `TELEGRAM_CHAT_ID` | Votre identifiant de discussion (ex. `123456789`) |
| `GEMINI_API_KEY` | Votre clé Google AI Studio (ex. `AIzaSy...`) |

---

### Étape 5 : Activer et tester sur GitHub Actions
1. Allez dans l'onglet **Actions** de votre dépôt GitHub (si vous venez de faire un Fork, cliquez sur le bouton vert **"I understand my workflows, go ahead and enable them"**).
2. Dans la colonne de gauche, cliquez sur **Daily Internship Job Alert**.
3. À droite, cliquez sur **Run workflow** ➔ puis sur le bouton vert **Run workflow**.
4. En **30 secondes**, vous recevez votre première alerte sur Telegram ! 🎉

---

## 🎨 Adapter le bot à votre profession (Architecte, Développeur, Finance, CDI, Stage...)

Toute la configuration se trouve dans un seul fichier ultra-simple : **[`search_config.json`](./search_config.json)**. Vous pouvez le modifier directement depuis l'interface web de GitHub (icône crayon ✏️).

### Paramètres disponibles dans `search_config.json`

| Champ | Description | Valeurs possibles |
| :--- | :--- | :--- |
| `alert_title` | Titre affiché en haut du message Telegram | Texte libre |
| `sector_label` | Lieu affiché dans l'en-tête Telegram | Texte libre (ex. `"Paris"`, `"Lyon"`, `"France"`) |
| `target_label` | Objectif affiché dans l'en-tête Telegram | Texte libre (ex. `"CDI Confirmé"`, `"Stage 6 mois"`) |
| `contract_type` | Filtre LinkedIn par type de contrat | `"internship"` (Stage/Alternance), `"full_time"` (CDI), `"contract"` (Freelance/CDD), `"part_time"`, `"any"` (Tous) |
| `time_window` | Fraîcheur des offres scannées | `"24h"`, `"3d"`, `"7d"`, `"30d"` |
| `max_offers_per_run` | Nombre maximum de nouvelles offres envoyées par jour | Nombre entier (ex. `10`) |
| `required_keywords_in_offer` | Mots-clés dont au moins un doit apparaître dans l'offre (laisser `[]` pour tout accepter) | Liste de mots (ex. `["stage", "intern"]` ou `[]`) |
| `excluded_keywords_in_title` | Mots-clés interdits dans le titre du poste | Liste de mots (ex. `["stage", "alternance"]` si vous cherchez un CDI) |
| `queries` | Liste des recherches `(keywords + location)` à effectuer | Liste d'objets `{"keywords": "...", "location": "..."}` |
| `gemini_context` | Instruction donnée à Gemini pour personnaliser le résumé | Texte décrivant votre profil et ce que vous cherchez |

---

### 📋 Exemples prêts à copier-coller dans `search_config.json`

#### Exemple 1 : Architecte (Bâtiment / Urbanisme / Paysage) en CDI à Paris & Lyon
```json
{
  "alert_title": "NOUVELLE(S) OFFRE(S) ARCHITECTE (CDI)",
  "sector_label": "Paris & Lyon",
  "target_label": "CDI Architecte DPLG / HMONP / Projet",
  "contract_type": "full_time",
  "time_window": "7d",
  "max_offers_per_run": 10,
  "required_keywords_in_offer": [
    "architecte",
    "architecture",
    "revit",
    "autocad",
    "maîtrise d'œuvre"
  ],
  "excluded_keywords_in_title": [
    "stage",
    "stagiaire",
    "alternance",
    "cloud",
    "software",
    "data"
  ],
  "queries": [
    { "keywords": "Architecte HMONP", "location": "Paris" },
    { "keywords": "Architecte Chef de Projet", "location": "Paris" },
    { "keywords": "Architecte DE", "location": "Lyon" }
  ],
  "gemini_context": "un Architecte (bâtiment / maîtrise d'œuvre) cherchant un CDI à Paris ou Lyon. Résume le type de projets (logements, tertiaire, réhabilitation), les logiciels demandés (Revit, AutoCAD, ArchiCAD) et l'expérience requise"
}
```

#### Exemple 2 : Architecte Cloud / Solutions Architect (CDI ou Freelance)
```json
{
  "alert_title": "NOUVELLE(S) OFFRE(S) CLOUD / SOLUTIONS ARCHITECT",
  "sector_label": "France & Télétravail",
  "target_label": "CDI / Freelance - AWS / GCP / Azure",
  "contract_type": "any",
  "time_window": "24h",
  "max_offers_per_run": 10,
  "required_keywords_in_offer": [],
  "excluded_keywords_in_title": [
    "stage",
    "stagiaire",
    "intern",
    "alternance"
  ],
  "queries": [
    { "keywords": "Cloud Architect AWS GCP", "location": "Paris" },
    { "keywords": "Solutions Architect", "location": "France" }
  ],
  "gemini_context": "un Cloud / Solutions Architect cherchant un poste en France. Précise le Cloud utilisé (AWS, GCP, Azure), la politique de télétravail et le niveau d'expérience demandé"
}
```

#### Exemple 3 : Stage Ingénieur Data / ML / AI (Configuration par défaut)
```json
{
  "alert_title": "NOUVELLE(S) OFFRE(S) DE STAGE (Data / ML / AI)",
  "sector_label": "Paris / La Défense & alentours",
  "target_label": "Stage 4A Ingénieur (~10 sem., 27 juin - 15 sept.)",
  "contract_type": "internship",
  "time_window": "7d",
  "max_offers_per_run": 10,
  "required_keywords_in_offer": [
    "stage",
    "stagiaire",
    "intern",
    "internship"
  ],
  "excluded_keywords_in_title": [
    "senior",
    "lead",
    "directeur",
    "manager",
    "cdi"
  ],
  "queries": [
    { "keywords": "Stage Data Engineer", "location": "Paris" },
    { "keywords": "Stage Machine Learning Engineer", "location": "Paris" },
    { "keywords": "Stage AI Engineer", "location": "Paris" },
    { "keywords": "Stage Data Engineer", "location": "La Défense" }
  ],
  "gemini_context": "un étudiant en 4ème année d'école d'ingénieur cherchant un stage de Data/ML/AI Engineer à Paris ou La Défense d'environ 10 semaines (entre le 27 juin et le 15 septembre)"
}
```

---

## ⏰ Changer l'heure d'envoi automatique

L'heure d'envoi est définie dans [`.github/workflows/daily_alert.yml`](./.github/workflows/daily_alert.yml) à la ligne `cron` (en temps universel UTC) :

```yaml
on:
  schedule:
    - cron: '0 7 * * *' # 07h00 UTC = 08h00 à Paris (hiver) / 09h00 à Paris (été)
```

- Pour recevoir l'alerte à **09h00 (heure d'hiver Paris)** : remplacez par `'0 8 * * *'`.
- Pour recevoir l'alerte **2 fois par jour (09h00 et 18h00)** : remplacez par `'0 8,17 * * *'`.

---

## 📄 Licence
Projet Open-Source sous licence MIT — libre d'utilisation, de modification et de partage !
