# tests/unit/test_stock.py
"""
Tests unitaires du module app/services/stock.py

Couvre :
    - verifier_stock()  → vérifie si le stock est suffisant
    - reserver_stock()  → décrémente le stock + invalide cache Redis
    - liberer_stock()   → incrémente le stock + met à jour cache Redis

Point clé : Redis est MOCKÉ dans tous les tests qui appellent
reserver_stock() ou liberer_stock() car ces fonctions appellent
redis_client.delete() ou redis_client.set().
Sans mock → ConnectionRefusedError car Redis n'est pas démarré.
"""

import pytest
from app.services.stock import verifier_stock, reserver_stock, liberer_stock
from app.models import Product

REDIS_MOCK_PATH = 'app.services.stock.redis_client'


  
# TESTS verifier_stock()
# Fonction pure : lit juste product.stock et retourne True/False.
# Pas besoin de mock Redis, aucun appel réseau.
  
@pytest.mark.unit
class TestVerifierStock:

    def test_stock_suffisant(self, product_sample):
        """
        Cas nominal : stock=10, demande=5 → True.
        product_sample est fourni par conftest.py (Laptop Pro, stock=10).
        5 <= 10 donc le stock est suffisant.
        """
        assert verifier_stock(product_sample, 5) is True

    def test_stock_insuffisant(self, product_sample):
        """
        Cas d'erreur : stock=10, demande=999 → False.
        999 > 10 donc le stock est insuffisant.
        """
        assert verifier_stock(product_sample, 999) is False

    def test_stock_exactement_disponible(self, product_sample):
        """
        Cas limite : demander exactement le stock disponible → True.
        stock=10, demande=10 → 10 <= 10 → True.
        Important : tester la frontière (ni trop ni trop peu).
        """
        assert verifier_stock(product_sample, 10) is True

    def test_quantite_zero_leve_exception(self, product_sample):
        """
        Quantité = 0 est invalide → ValueError.
        On ne peut pas commander 0 article.
        """
        with pytest.raises(ValueError):
            verifier_stock(product_sample, 0)

    def test_quantite_negative_leve_exception(self, product_sample):
        """
        Quantité négative est invalide → ValueError.
        Une quantité doit toujours être > 0.
        """
        with pytest.raises(ValueError):
            verifier_stock(product_sample, -1)


  
# TESTS reserver_stock()
#
# Cette fonction fait 3 choses :
#   1. Vérifie que le stock est suffisant
#   2. Décrémente product.stock en BDD (session.commit)
#   3. Invalide le cache Redis (redis_client.delete)
#
# → Redis DOIT être mocké pour éviter ConnectionRefusedError
# → On vérifie ensuite que delete() a bien été appelé
  

class TestReserverStock:

    def test_reservation_reussie(self, product_sample, db_session, mocker):
        """
        Cas nominal : réservation de 3 unités sur stock=10.

        Étapes du test :
            1. Mocker Redis → remplace redis_client par un faux objet
            2. Appeler reserver_stock()
            3. Vérifier que le stock a diminué de 3
            4. Vérifier que Redis.delete() a bien été appelé
               (le cache doit être invalidé après une modification de stock)
        """
        # Étape 1 : mocker Redis
        # mock_redis est un faux objet qui accepte tous les appels
        # sans contacter le vrai Redis
        mock_redis = mocker.patch(REDIS_MOCK_PATH)

        # Mémoriser le stock avant la réservation
        stock_avant = product_sample.stock   # = 10

        # Étape 2 : appeler la fonction à tester
        updated = reserver_stock(product_sample, 3, db_session)

        # Étape 3 : vérifier que le stock a bien diminué
        # 10 - 3 = 7 unités restantes
        assert updated.stock == stock_avant - 3

        # Étape 4 : vérifier que Redis.delete() a été appelé exactement 1 fois
        # Si delete() n'est pas appelé → le cache garde l'ancien stock
        # → les clients verraient un stock incorrect
        mock_redis.delete.assert_called_once()

    def test_reservation_verifie_cle_redis(self, product_sample, db_session, mocker):
        """
        Vérifie que Redis.delete() est appelé avec la BONNE clé.
        La clé doit identifier précisément le produit modifié.
        Format attendu : "product:{id}:stock"
        """
        mock_redis = mocker.patch(REDIS_MOCK_PATH)

        reserver_stock(product_sample, 1, db_session)

        # Vérifier la clé exacte passée à delete()
        expected_key = f"product:{product_sample.id}:stock"
        mock_redis.delete.assert_called_once_with(expected_key)

    def test_stock_insuffisant_leve_exception(self, product_sample, db_session, mocker):
        """
        Stock insuffisant → ValueError avec message 'insuffisant'.
        stock=10, demande=999 → impossible → exception levée.

        Redis est quand même mocké car la fonction appelle
        verifier_stock() avant d'accéder à Redis.
        """
        mocker.patch(REDIS_MOCK_PATH)

        with pytest.raises(ValueError, match='insuffisant'):
            reserver_stock(product_sample, 999, db_session)

    def test_stock_insuffisant_ne_modifie_pas_bdd(self, product_sample, db_session, mocker):
        """
        Si le stock est insuffisant, la BDD ne doit PAS être modifiée.
        Le stock doit rester à 10 après l'échec de la réservation.
        """
        mocker.patch(REDIS_MOCK_PATH)
        stock_avant = product_sample.stock   # = 10

        # La réservation échoue
        with pytest.raises(ValueError):
            reserver_stock(product_sample, 999, db_session)

        # Le stock ne doit PAS avoir changé
        assert product_sample.stock == stock_avant

    def test_redis_non_appele_si_exception(self, product_sample, db_session, mocker):
        """
        Si la réservation échoue (stock insuffisant),
        Redis.delete() ne doit PAS être appelé.
        Aucune raison d'invalider le cache si rien n'a changé.
        """
        mock_redis = mocker.patch(REDIS_MOCK_PATH)

        with pytest.raises(ValueError):
            reserver_stock(product_sample, 999, db_session)

        # delete() ne doit pas avoir été appelé
        mock_redis.delete.assert_not_called()


  
# TESTS liberer_stock()
#
# Cette fonction fait 3 choses :
#   1. Vérifie que la quantité est valide (> 0)
#   2. Incrémente product.stock en BDD (session.commit)
#   3. Met à jour le cache Redis (redis_client.set)
#
# Cas d'usage : annulation d'une commande → stock restitué
  

    def test_liberation_stock(self, product_sample, db_session, mocker):
        """
        Cas nominal : libérer 2 unités → stock augmente de 2.

        Étapes du test :
            1. Mocker Redis
            2. Appeler liberer_stock()
            3. Vérifier que le stock a augmenté de 2
            4. Vérifier que Redis.set() a bien été appelé
               (le cache doit être mis à jour avec le nouveau stock)
        """
        # Étape 1 : mocker Redis
        mock_redis = mocker.patch(REDIS_MOCK_PATH)

        # Mémoriser le stock avant la libération
        stock_avant = product_sample.stock   # = 10

        # Étape 2 : libérer 2 unités
        updated = liberer_stock(product_sample, 2, db_session)

        # Étape 3 : vérifier que le stock a bien augmenté
        # 10 + 2 = 12 unités
        assert updated.stock == stock_avant + 2

        # Étape 4 : vérifier que Redis.set() a été appelé exactement 1 fois
        # set() met à jour le cache avec le nouveau stock
        mock_redis.set.assert_called_once()

    def test_liberation_verifie_arguments_redis(self, product_sample, db_session, mocker):
        """
        Vérifie que Redis.set() est appelé avec la bonne clé ET la bonne valeur.
        La valeur doit être le NOUVEAU stock (après libération).
        """
        mock_redis = mocker.patch(REDIS_MOCK_PATH)

        updated = liberer_stock(product_sample, 3, db_session)

        # Vérifier la clé et la valeur passées à set()
        expected_key = f"product:{product_sample.id}:stock"
        mock_redis.set.assert_called_once_with(expected_key, updated.stock)