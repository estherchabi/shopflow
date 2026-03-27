# tests/unit/test_pricing.py
"""
Tests unitaires du module app/services/pricing.py

Couvre :
    - calcul_prix_ttc()   → conversion HT vers TTC avec TVA 20%
    - appliquer_coupon()  → application d'une réduction sur un prix
    - calculer_total()    → total TTC d'une liste de produits avec coupon
"""

import pytest
from app.services.pricing import calcul_prix_ttc, appliquer_coupon, calculer_total
from app.models import Product, Coupon


#  
# TESTS calcul_prix_ttc()
# Fonction pure — pas besoin de BDD ni de fixtures
#  

@pytest.mark.unit   # marker personnalisé pour filtrer : pytest -m unit
class TestCalculPrixTtc:

    def test_prix_normal(self):
        """Cas nominal : 100€ HT × 1.20 = 120€ TTC."""
        assert calcul_prix_ttc(100.0) == 120.0

    def test_prix_zero(self):
        """Cas limite : 0€ HT → 0€ TTC (pas d'erreur attendue)."""
        assert calcul_prix_ttc(0.0) == 0.0

    def test_arrondi_deux_decimales(self):
        """Le résultat doit être arrondi à 2 décimales — pas 12.000000001."""
        assert calcul_prix_ttc(10.0) == 12.0

    def test_prix_negatif_leve_exception(self):
        """
        Un prix négatif est invalide → ValueError attendue.
        match='invalide' vérifie que le MESSAGE contient 'invalide'
        et pas juste n'importe quelle ValueError.
        """
        with pytest.raises(ValueError, match='invalide'):
            calcul_prix_ttc(-5.0)

    @pytest.mark.parametrize('ht,ttc', [
        (50.0,   60.0),    # 50 × 1.20 = 60
        (199.99, 239.99),  # arrondi à 2 décimales
        (0.01,   0.01),    # très petit montant
    ])
    def test_parametrise(self, ht, ttc):
        """
        Paramétrisation : teste plusieurs couples (HT, TTC) en un seul test.
        pytest génère automatiquement 3 cas de test distincts.
        """
        assert calcul_prix_ttc(ht) == ttc


#  
# TESTS appliquer_coupon()
# Utilise la fixture coupon_sample (PROMO20, 20%, actif=True)
#  

class TestAppliquerCoupon:

    def test_reduction_20_pourcent(self, coupon_sample):
        """
        Cas nominal : PROMO20 appliqué sur 100€ → 80€.
        coupon_sample est fourni par conftest.py (PROMO20, reduction=20%).
        100 × (1 - 0.20) = 80.0
        """
        result = appliquer_coupon(100.0, coupon_sample)
        assert result == 80.0

    def test_coupon_inactif_leve_exception(self, db_session):
        """
        Un coupon inactif (actif=False) doit lever ValueError.
        On crée un coupon inactif directement sans le persister en BDD
        car appliquer_coupon() ne fait pas de requête SQL.
        """
        coupon_inactif = Coupon(code='OLD', reduction=10.0, actif=False)
        with pytest.raises(ValueError, match='inactif'):
            appliquer_coupon(100.0, coupon_inactif)

    def test_reduction_invalide(self, coupon_sample):
        """
        Une réduction > 100% est invalide → ValueError attendue.
        150% de réduction n'a pas de sens mathématique.
        """
        coupon_invalide = Coupon(code='BAD', reduction=150.0, actif=True)
        with pytest.raises(ValueError):
            appliquer_coupon(100.0, coupon_invalide)


#  
# TESTS PARAMÉTRÉS — appliquer_coupon() avec plusieurs réductions
# Teste 4 cas en une seule fonction grâce à @pytest.mark.parametrize
#  

@pytest.mark.parametrize('reduction,prix_initial,prix_attendu', [
    (10,  100.0,  90.0),   # -10% : 100 × 0.90 = 90
    (50,  200.0, 100.0),   # -50% : 200 × 0.50 = 100
    (100,  50.0,   0.0),   # -100% : gratuit = 0
    (1,   100.0,  99.0),   # -1% minimal : 100 × 0.99 = 99
])
def test_coupon_reductions_diverses(reduction, prix_initial, prix_attendu, db_session):
    """
    Vérifie que différents taux de réduction donnent les bons résultats.
    Le coupon est créé en mémoire (pas besoin de le persister en BDD).
    pytest génère 4 tests séparés avec des noms explicites :
        test_coupon_reductions_diverses[10-100.0-90.0]
        test_coupon_reductions_diverses[50-200.0-100.0]
        ...
    """
    coupon = Coupon(code=f'TEST{reduction}', reduction=float(reduction), actif=True)
    assert appliquer_coupon(prix_initial, coupon) == prix_attendu


#  
# TEST calculer_total() avec coupon
#  

def test_calculer_total_avec_coupon(db_session, coupon_sample):
    """
    Scénario complet : 2 produits + coupon PROMO20.

    Calcul attendu :
        p1 : 50€ HT
        p2 : 30€ HT
        ─────────────
        Total HT  : 80€
        TVA 20%   : +16€
        Total TTC : 96€
        PROMO20   : -20% → 96 × 0.80 = 76.80€

    Les produits sont insérés en BDD car calculer_total()
    accède à product.price via l'objet SQLAlchemy.
    """
    # Créer 2 produits et les insérer en BDD
    p1 = Product(name='Produit A', price=50.0, stock=5)
    p2 = Product(name='Produit B', price=30.0, stock=5)
    db_session.add_all([p1, p2])
    db_session.commit()

    # Calculer le total avec le coupon PROMO20
    result = calculer_total([(p1, 1), (p2, 1)], coupon=coupon_sample)

    # Vérifier le résultat : 96€ TTC - 20% = 76.80€
    assert result == 76.80