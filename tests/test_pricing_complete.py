# tests/unit/test_pricing.py
"""
Tests unitaires du module app/services/pricing.py

Couvre :
    - calcul_prix_ttc()    → conversion HT vers TTC avec TVA 20%
    - appliquer_coupon()   → application d'une réduction sur un prix
    - calculer_total()     → total TTC d'une liste de produits avec coupon
    - calculer_remise()    → calcul du pourcentage de remise appliqué (NOUVEAU)
"""

import pytest
from app.services.pricing import (
    calcul_prix_ttc,
    appliquer_coupon,
    calculer_total,
    calculer_remise,    # ← nouvelle fonction à tester
)
from app.models import Product, Coupon


# ══════════════════════════════════════════════════════════════
# TESTS calcul_prix_ttc()
# Fonction pure — pas besoin de BDD ni de fixtures
# ══════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestCalculPrixTtc:

    def test_prix_normal(self):
        """Cas nominal : 100€ HT × 1.20 = 120€ TTC."""
        assert calcul_prix_ttc(100.0) == 120.0

    def test_prix_zero(self):
        """Cas limite : 0€ HT → 0€ TTC (pas d'erreur attendue)."""
        assert calcul_prix_ttc(0.0) == 0.0

    def test_arrondi_deux_decimales(self):
        """Le résultat doit être arrondi à 2 décimales."""
        assert calcul_prix_ttc(10.0) == 12.0

    def test_prix_negatif_leve_exception(self):
        """
        Un prix négatif est invalide → ValueError attendue.
        match='invalide' vérifie que le message contient 'invalide'.
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
        Paramétrisation : teste 3 couples (HT → TTC) en une seule fonction.
        pytest génère automatiquement 3 tests distincts.
        """
        assert calcul_prix_ttc(ht) == ttc


# ══════════════════════════════════════════════════════════════
# TESTS appliquer_coupon()
# Utilise la fixture coupon_sample (PROMO20, 20%, actif=True)
# ══════════════════════════════════════════════════════════════

class TestAppliquerCoupon:

    def test_reduction_20_pourcent(self, coupon_sample):
        """
        Cas nominal : PROMO20 appliqué sur 100€ → 80€.
        100 × (1 - 0.20) = 80.0
        """
        result = appliquer_coupon(100.0, coupon_sample)
        assert result == 80.0

    def test_coupon_inactif_leve_exception(self, db_session):
        """
        Coupon inactif (actif=False) → ValueError avec message 'inactif'.
        Le coupon est créé en mémoire, pas besoin de le persister en BDD.
        """
        coupon_inactif = Coupon(code='OLD', reduction=10.0, actif=False)
        with pytest.raises(ValueError, match='inactif'):
            appliquer_coupon(100.0, coupon_inactif)

    def test_reduction_invalide(self, coupon_sample):
        """
        Réduction > 100% est invalide → ValueError attendue.
        150% de réduction n'a pas de sens.
        """
        coupon_invalide = Coupon(code='BAD', reduction=150.0, actif=True)
        with pytest.raises(ValueError):
            appliquer_coupon(100.0, coupon_invalide)

    def test_reduction_zero_invalide(self):
        """
        Réduction = 0% est invalide (doit être > 0).
        La condition dans pricing.py est : 0 < reduction <= 100.
        """
        coupon_zero = Coupon(code='ZERO', reduction=0.0, actif=True)
        with pytest.raises(ValueError, match='invalide'):
            appliquer_coupon(100.0, coupon_zero)


@pytest.mark.parametrize('reduction,prix_initial,prix_attendu', [
    (10,  100.0,  90.0),   # -10% : 100 × 0.90 = 90
    (50,  200.0, 100.0),   # -50% : 200 × 0.50 = 100
    (100,  50.0,   0.0),   # -100% : gratuit = 0
    (1,   100.0,  99.0),   # -1% minimal : 100 × 0.99 = 99
])
def test_coupon_reductions_diverses(reduction, prix_initial, prix_attendu, db_session):
    """
    Vérifie que différents taux de réduction donnent les bons résultats.
    pytest génère 4 tests séparés avec des noms explicites :
        test_coupon_reductions_diverses[10-100.0-90.0]
        test_coupon_reductions_diverses[50-200.0-100.0]
        ...
    """
    coupon = Coupon(code=f'TEST{reduction}', reduction=float(reduction), actif=True)
    assert appliquer_coupon(prix_initial, coupon) == prix_attendu


# ══════════════════════════════════════════════════════════════
# TESTS calculer_total()
# ══════════════════════════════════════════════════════════════

def test_calculer_total_liste_vide():
    """
    Liste vide → retourne 0.0 sans erreur.
    Cas important : pas de produits = pas de total.
    """
    assert calculer_total([]) == 0.0


def test_calculer_total_sans_coupon(db_session):
    """
    Total TTC sans coupon : 1 produit à 100€ HT → 120€ TTC.
    100 × 1.20 = 120.0
    """
    p = Product(name='PC', price=100.0, stock=5)
    result = calculer_total([(p, 1)])
    assert result == 120.0


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
    """
    p1 = Product(name='Produit A', price=50.0, stock=5)
    p2 = Product(name='Produit B', price=30.0, stock=5)
    db_session.add_all([p1, p2])
    db_session.commit()

    result = calculer_total([(p1, 1), (p2, 1)], coupon=coupon_sample)

    # 80 HT → 96 TTC → -20% → 76.80€
    assert result == 76.80


def test_calculer_total_quantite_multiple(db_session):
    """
    Quantité > 1 : 3 × 10€ HT = 30€ HT → 36€ TTC.
    Vérifie que la quantité est bien multipliée par le prix.
    """
    p = Product(name='Souris', price=10.0, stock=10)
    result = calculer_total([(p, 3)])
    # 30 HT × 1.20 = 36 TTC
    assert result == 36.0


# ══════════════════════════════════════════════════════════════
# TESTS calculer_remise()  ← NOUVELLE FONCTION
#
# calculer_remise() fait l'opération INVERSE de appliquer_coupon() :
# elle calcule QUEL pourcentage de remise a été appliqué
# à partir du prix original et du prix final.
#
# Formule : remise = (1 - prix_final / prix_original) × 100
# Exemple  : prix_original=100, prix_final=80 → remise = 20%
# ══════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestCalculerRemise:

    def test_remise_20_pourcent(self):
        """
        Cas nominal : 100€ → 80€ = 20% de remise.
        (1 - 80/100) × 100 = 20.0
        """
        assert calculer_remise(100.0, 80.0) == 20.0

    def test_remise_50_pourcent(self):
        """
        200€ → 100€ = 50% de remise.
        (1 - 100/200) × 100 = 50.0
        """
        assert calculer_remise(200.0, 100.0) == 50.0

    def test_aucune_remise(self):
        """
        Prix final = prix original → 0% de remise.
        (1 - 100/100) × 100 = 0.0
        """
        assert calculer_remise(100.0, 100.0) == 0.0

    def test_remise_100_pourcent(self):
        """
        Prix final = 0€ → 100% de remise (produit gratuit).
        (1 - 0/100) × 100 = 100.0
        """
        assert calculer_remise(100.0, 0.0) == 100.0

    def test_arrondi_deux_decimales(self):
        """
        Le résultat est arrondi à 2 décimales.
        (1 - 66.67/100) × 100 = 33.33%
        """
        assert calculer_remise(100.0, 66.67) == 33.33

    def test_prix_original_zero_leve_exception(self):
        """
        Prix original = 0 → ValueError (division par zéro).
        La condition dans pricing.py : if prix_original <= 0
        """
        with pytest.raises(ValueError, match='invalide'):
            calculer_remise(0.0, 50.0)

    def test_prix_original_negatif_leve_exception(self):
        """
        Prix original négatif → ValueError.
        Un prix ne peut pas être négatif.
        """
        with pytest.raises(ValueError, match='invalide'):
            calculer_remise(-10.0, 5.0)

    @pytest.mark.parametrize('original,final,remise_attendue', [
        (100.0,  90.0, 10.0),   # -10%
        (200.0, 150.0, 25.0),   # -25%
        (50.0,   25.0, 50.0),   # -50%
        (100.0,   0.0, 100.0),  # -100% = gratuit
    ])
    def test_parametrise_remises(self, original, final, remise_attendue):
        """
        Paramétrisation : vérifie 4 couples (original, final) → remise%.
        Permet de couvrir plusieurs cas sans dupliquer le code.
        """
        assert calculer_remise(original, final) == remise_attendue