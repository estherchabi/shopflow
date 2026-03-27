
## Package requirement : À quoi il sert 

| Package | À quoi il sert |
|---|---|
| `fastapi==0.110.0` | Framework web Python pour créer l'API REST de ShopFlow avec validation automatique et documentation Swagger intégrée. |
| `uvicorn[standard]==0.29.0` | Serveur ASGI qui exécute l'application FastAPI — c'est lui qui écoute sur le port 8000. |
| `sqlalchemy==2.0.28` | ORM qui traduit les classes Python (`Product`, `Order`…) en tables SQL et les opérations Python en requêtes SQL. |
| `pydantic==2.6.4` | Valide et structure les données entrantes et sortantes de l'API (schémas `ProductCreate`, `OrderResponse`…). |
| `pydantic-settings==2.2.1` | Charge la configuration de l'application depuis les variables d'environnement ou un fichier `.env`. |
| `redis==5.0.3` | Client Python pour communiquer avec le serveur Redis — utilisé pour lire, écrire et supprimer les entrées du cache. |
| `httpx==0.27.0` | Client HTTP asynchrone utilisé par le `TestClient` de FastAPI pour envoyer de vraies requêtes HTTP dans les tests d'intégration. |
| `faker==24.3.0` | Génère des données de test réalistes (noms, emails, prix…) pour alimenter les fixtures sans saisir de valeurs à la main. |
| `pytest==8.1.1` | Framework de tests principal — découvre, exécute et rapporte tous les tests unitaires et d'intégration de ShopFlow. |
| `pytest-cov==5.0.0` | Plugin pytest qui mesure la couverture de code et génère les rapports HTML et XML utilisés par SonarQube. |
| `pytest-mock==3.12.0` | Plugin pytest qui fournit la fixture `mocker` pour remplacer Redis, SMTP ou tout service externe par un `MagicMock`. |
| `pytest-asyncio==0.23.6` | Plugin pytest qui permet de tester les fonctions `async/await` de FastAPI nativement sans adaptateur manuel. |
| `pytest-xdist==3.5.0` | Plugin pytest qui parallélise l'exécution des tests sur plusieurs CPU — `pytest -n auto` divise le temps d'exécution par le nombre de cœurs. |
| `locust==2.24.1` | Outil de tests de charge qui simule des centaines d'utilisateurs simultanés sur l'API ShopFlow pour mesurer les performances. |
| `bandit==1.7.8` | Analyseur de sécurité statique qui scanne le code Python à la recherche de vulnérabilités connues (mots de passe codés en dur, SSL désactivé…). |
| `pylint==3.1.0` | Analyseur de qualité de code qui vérifie les conventions, détecte les erreurs potentielles et mesure les code smells intégrés dans SonarQube. |
| `flake8==7.0.0` | Vérificateur de style PEP8 léger et rapide — utilisé comme premier stage du pipeline Jenkins pour un feedback en quelques secondes. |








## Xcode
L'erreur vient de **gevent** qui échoue à compiler sur votre Mac Apple Silicon (arm64) car le compilateur C n'est pas disponible.

**Cause :** `gevent` est une dépendance de `locust` — elle nécessite les outils de développement Xcode pour compiler du code C.

---

**Solution 1 — Installer les outils Xcode (recommandée)**

```bash
xcode-select --install
```

Une fenêtre s'ouvre → cliquer sur **Installer** → attendre ~5 minutes → relancer :

```bash
pip install -r requirements.txt
```

---

**Solution 2 — Si Xcode est déjà installé mais mal configuré**

```bash
sudo xcode-select --reset
xcode-select --print-path   # Le chemin affiché doit être /Library/Developer/CommandLineTools ou /Applications/Xcode.app/Contents/Developer.

# Accepter la licence Xcode
sudo xcodebuild -license accept


pip install -r requirements.txt
```

---

**Solution 3 — Forcer l'installation de gevent via une wheel pré-compilée**

```bash
pip install gevent --only-binary=:all:
pip install -r requirements.txt
```

---

**Solution 4 — Si locust n'est pas utilisé tout de suite (TP1/TP2/TP3)**

Vous pouvez commenter temporairement locust dans `requirements.txt` pour avancer sans blocage :

```
# locust==2.24.1   ← commenter pour l'instant
```

```bash
pip install -r requirements.txt
```

Locust ne sera nécessaire qu'en **TP4**. Vous pouvez l'installer séparément plus tard une fois Xcode configuré.

---

La solution la plus simple est la **Solution 1** — `xcode-select --install` règle définitivement le problème sur Mac.




## ERROR:    [Errno 48] Address already in use
kill -9 $(lsof -t -i :8000)                             
