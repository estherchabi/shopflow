# tests/integration/test_products_api.py
import pytest

@pytest.mark.integration
class TestListProducts:

    def test_liste_vide_au_demarrage(self, client):
        """Sans données, GET /products/ retourne une liste vide."""
        response = client.get('/products/')
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_produit_cree_apparait_dans_liste(self, client, api_product):
        response = client.get('/products/')
        assert response.status_code == 200
        ids = [p['id'] for p in response.json()]
        assert api_product['id'] in ids

    def test_filtre_par_categorie(self, client):
        # Créer un produit avec catégorie spécifique
        client.post('/products/', json={
            'name': 'GPU RTX', 'price': 799.0, 'stock': 3, 'category': 'gpu'
        })
        response = client.get('/products/?category=gpu')
        assert response.status_code == 200
        for p in response.json():
            assert p['category'] == 'gpu'

    def test_pagination_limit(self, client):
        for i in range(5):
            client.post('/products/', json={'name': f'Prod{i}', 'price': 10.0, 'stock': 1})
        response = client.get('/products/?limit=2')
        assert response.status_code == 200
        assert len(response.json()) <= 2

    def test_pagination_skip(self, client):
        """skip=1000 → liste vide ou résultats après le 1000e."""
        response = client.get('/products/?skip=1000&limit=10')
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.integration
class TestGetProduct:

    def test_get_produit_existant(self, client, api_product):
        pid = api_product['id']
        response = client.get(f'/products/{pid}')
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == pid
        assert data['name'] == api_product['name']

    def test_get_produit_inexistant_retourne_404(self, client):
        response = client.get('/products/99999')
        assert response.status_code == 404

    def test_schema_complet(self, client, api_product):
        """La réponse contient tous les champs attendus."""
        response = client.get(f'/products/{api_product["id"]}')
        data = response.json()
        for field in ['id', 'name', 'price', 'stock', 'active', 'created_at']:
            assert field in data, f'Champ manquant : {field}'


#tests/integration/test_products_api.py — écriture
@pytest.mark.integration
class TestCreateProduct:

    def test_creation_valide(self, client):
        payload = {'name': 'Souris Ergonomique', 'price': 49.99, 'stock': 30}
        response = client.post('/products/', json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data['name'] == 'Souris Ergonomique'
        assert data['price'] == 49.99
        assert data['id'] is not None

    def test_creation_prix_negatif_422(self, client):
        response = client.post('/products/', json={'name': 'X', 'price': -10.0, 'stock': 5})
        assert response.status_code == 422

    def test_creation_nom_vide_422(self, client):
        response = client.post('/products/', json={'name': '', 'price': 10.0, 'stock': 5})
        assert response.status_code == 422

    def test_creation_stock_negatif_422(self, client):
        response = client.post('/products/', json={'name': 'T', 'price': 10.0, 'stock': -1})
        assert response.status_code == 422

    def test_active_true_par_defaut(self, client):
        response = client.post('/products/', json={'name': 'Actif', 'price': 1.0, 'stock': 1})
        assert response.json()['active'] is True

@pytest.mark.integration
class TestUpdateDeleteProduct:

    def test_mise_a_jour_prix(self, client, api_product):
        pid = api_product['id']
        response = client.put(f'/products/{pid}', json={'price': 79.99})
        assert response.status_code == 200
        assert response.json()['price'] == 79.99

    def test_mise_a_jour_stock(self, client, api_product):
        pid = api_product['id']
        response = client.put(f'/products/{pid}', json={'stock': 100})
        assert response.status_code == 200
        assert response.json()['stock'] == 100

    def test_suppression_soft_delete(self, client):
        """DELETE désactive le produit (soft delete) — il n'est plus accessible."""
        create = client.post('/products/', json={'name': 'A supprimer', 'price': 1.0, 'stock': 1})
        pid = create.json()['id']
        response = client.delete(f'/products/{pid}')
        assert response.status_code == 204
        # Vérifier que le produit n'est plus accessible
        get_resp = client.get(f'/products/{pid}')
        assert get_resp.status_code == 404


    # reponse q2.4 test_filtre_prix_min_max()
    def test_filtre_prix_min_max(self, client):
        """GET /products/?min_price=50&max_price=200 retourne seulement les produits
        dont le prix est entre 50€ et 200€ inclus."""
        # Créer 3 produits avec des prix différents
        client.post('/products/', json={'name': 'Bon marché', 'price': 10.0, 'stock': 1})
        client.post('/products/', json={'name': 'Dans la fourchette', 'price': 100.0, 'stock': 1})
        client.post('/products/', json={'name': 'Trop cher', 'price': 500.0, 'stock': 1})

        # Filtrer : min=50, max=200
        response = client.get('/products/?min_price=50&max_price=200')
        assert response.status_code == 200
        results = response.json()

        # Vérifier que tous les résultats sont dans la fourchette
        for p in results:
            assert 50 <= p['price'] <= 200, \
                f"Produit hors fourchette : {p['name']} à {p['price']}€"

        # Vérifier que 'Dans la fourchette' (100€) est bien présent
        noms = [p['name'] for p in results]
        assert 'Dans la fourchette' in noms

        # Vérifier que les produits hors fourchette sont absents
        assert 'Bon marché' not in noms      # 10€ < 50€
        assert 'Trop cher' not in noms        # 500€ > 200€
