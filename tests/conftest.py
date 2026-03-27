# tests/conftest.py
"""
Fichier de configuration pytest — Fixtures partagées entre tous les tests.

Les fixtures définies ici sont automatiquement disponibles dans tous les
fichiers de test sans avoir besoin de les importer.

Hiérarchie des fixtures :
    db_engine → db_session → product_sample / coupon_sample
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import Product, Cart, CartItem, Order, Coupon

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
import uuid
from faker import Faker

fake = Faker()

# FIXTURES BASE DE DONNÉES

@pytest.fixture(scope="module")
def db_engine():
    """
    Crée un moteur SQLite en mémoire (RAM) pour les tests.



    sqlite:///:memory: = BDD en RAM (pas de fichier sur le disque)
    → rapide, isolée, détruite automatiquement après chaque test.

    StaticPool : oblige SQLite à utiliser une seule connexion partagée.
    Obligatoire avec :memory: sinon chaque thread voit une BDD différente.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,   # une seule connexion partagée (obligatoire pour :memory:)
    )

    # Crée toutes les tables définies dans app/models.py
    # (Product, Cart, CartItem, Order, OrderItem, Coupon)
    Base.metadata.create_all(engine)

    yield engine   # ← le test s'exécute ici

    # Teardown automatique : supprime toutes les tables après le test
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Fournit une session SQLAlchemy fraîche pour chaque test.

    La session est l'objet de travail SQLAlchemy — c'est via elle
    qu'on fait les INSERT, SELECT, UPDATE, DELETE.

    scope="function" : une nouvelle session pour chaque test individuel.

    Le rollback() final annule toutes les écritures du test :
    même si on oublie de nettoyer les données dans le test,
    la prochaine session repart d'une BDD propre.

    Schéma d'exécution pour chaque test :
        1. Ouvrir la session
        2. Exécuter le test (yield)
        3. Rollback → annule tous les INSERT/UPDATE/DELETE du test
        4. Fermer la session
    """
    Session = sessionmaker(bind=db_engine)
    session = Session()

    yield session   # ← le test reçoit cet objet session

    # Teardown : annule toutes les modifications du test
    session.rollback()
    session.close()


# ══════════════════════════════════════════════════════════════
# FIXTURES DE DONNÉES — objets prêts à l'emploi dans les tests
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def product_sample(db_session):
    """
    Crée et insère un produit exemple dans la BDD de test.

    Utilisé dans les tests qui ont besoin d'un produit existant,
    par exemple pour tester reserver_stock() ou ajouter_au_panier().

    Données :
        name  = 'Laptop Pro'
        price = 999.99 € HT
        stock = 10 unités disponibles

    Utilisation dans un test :
        def test_mon_test(product_sample):
            assert product_sample.stock == 10
    """
    p = Product(
        name="Laptop Pro",
        price=999.99,   # prix HT en euros
        stock=10        # 10 unités disponibles
    )
    db_session.add(p)
    db_session.commit()       # INSERT en base
    db_session.refresh(p)     # recharge l'objet pour récupérer l'id auto-généré
    return p


@pytest.fixture
def coupon_sample(db_session):
    """
    Crée et insère un coupon de réduction exemple dans la BDD de test.

    Utilisé dans les tests qui ont besoin d'un coupon valide,
    par exemple pour tester appliquer_coupon() ou calculer_total().

    Données :
        code      = 'PROMO20'  → identifiant unique du coupon
        reduction = 20.0       → 20% de réduction
        actif     = True       → coupon utilisable

    Exemple d'effet :
        100€ TTC avec PROMO20 → 100 × (1 - 0.20) = 80€

    Utilisation dans un test :
        def test_mon_test(coupon_sample):
            assert coupon_sample.reduction == 20.0
    """
    c = Coupon(
        code=f"PROMO20_{uuid.uuid4().hex[:6]}", #code="PROMO20" (non unique), code=fake.bothify(text="PROMO####"),
        reduction=20.0,   # 20% de réduction
        actif=True        # coupon actif = utilisable
    )
    db_session.add(c)
    db_session.commit()   # INSERT en base
    return c




# TESTCLIENT FASTAPI 
@pytest.fixture(scope='module')
def client(db_engine):
    """TestClient FastAPI avec BDD SQLite isolée par module de test."""
    SessionTest = sessionmaker(bind=db_engine)

    def override_get_db():
        session = SessionTest()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# FIXTURES API 
@pytest.fixture
def api_product(client):
    """Crée un produit via POST /products/ et le retourne."""
    response = client.post('/products/', json={
        'name': 'Clavier Mécanique',
        'price': 89.99,
        'stock': 25,
        'category': 'peripheriques',
    })
    assert response.status_code == 201
    yield response.json()
    # Cleanup : désactiver le produit après le test
    client.delete(f'/products/{response.json()["id"]}')

@pytest.fixture
def api_coupon(client):
    """Crée un coupon TEST10 (-10%) via POST /coupons/."""
    response = client.post('/coupons/', json={
        'code': 'TEST10', 'reduction': 10.0, 'actif': True
    })
    assert response.status_code == 201
    yield response.json()




@pytest.fixture
def fake_product_data():
    """Génère un payload produit réaliste et aléatoire."""
    return {
        'name':     fake.catch_phrase()[:50],   # ex: 'Synergistic Rubber Chair'
        'price':    round(fake.pyfloat(min_value=1, max_value=2000, right_digits=2), 2),
        'stock':    fake.random_int(min=0, max=500),
        'category': fake.random_element(['informatique', 'peripheriques', 'audio', 'gaming']),
        'description': fake.sentence(nb_words=10),
    }

@pytest.fixture
def multiple_products(client):
    """Crée 5 produits avec faker pour tester la liste et les filtres."""
    faker_inst = Faker()
    products = []
    for i in range(5):
        r = client.post('/products/', json={
            'name': faker_inst.word().capitalize() + f' {i}',
            'price': round(10.0 + i * 20, 2),
            'stock': 10,
        })
        products.append(r.json())
    yield products
    # Cleanup : désactiver les 5 produits
    for p in products:
        client.delete(f'/products/{p["id"]}')
