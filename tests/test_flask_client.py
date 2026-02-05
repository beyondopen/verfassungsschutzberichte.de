"""Flask test-client tests (need app context but NOT a running server)."""


class TestGetIndex:
    """Test the get_index helper via the /api endpoint using the test client."""

    def test_api_returns_index(self):
        from app import app
        with app.test_client() as client:
            response = client.get('/api')
            assert response.status_code == 200
            data = response.get_json()
            assert 'reports' in data
            assert 'total' in data
            assert isinstance(data['reports'], list)


class TestBlogFunctions:
    """Test blog-related routes via the Flask test client."""

    def test_blog_index(self):
        from app import app
        with app.test_client() as client:
            response = client.get('/blog/')
            assert response.status_code == 200
            assert b'Blog' in response.data

    def test_blog_post_exists(self):
        from app import app
        with app.test_client() as client:
            response = client.get('/blog/launch')
            assert response.status_code == 200

    def test_blog_post_not_found(self):
        from app import app
        with app.test_client() as client:
            response = client.get('/blog/nonexistent-slug-xyz')
            assert response.status_code == 404


class TestNonDebugBranches:
    """Test code paths that only execute when app.debug is False."""

    def test_trends_redirect_without_query(self):
        """Test that /trends redirects when no query and debug=False."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/trends')
                assert response.status_code == 302
                assert '/trends?q=nsu&q=raf' in response.headers['Location']
        finally:
            app.debug = True

    def test_regional_redirect_without_query(self):
        """Test that /regional redirects when no query and debug=False."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/regional')
                assert response.status_code == 302
                assert '/regional?q=vvn-bda' in response.headers['Location']
        finally:
            app.debug = True

    def test_pdf_download_non_debug(self):
        """Test PDF download uses X-Accel-Redirect in non-debug mode."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/pdfs/test-bund-2020.pdf')
                assert response.status_code == 200
                assert response.headers['Content-Type'] == 'application/pdf'
                assert response.headers['X-Accel-Redirect'] == '/internal-pdfs/test-bund-2020.pdf'
                assert 'noindex' in response.headers.get('X-Robots-Tag', '')
        finally:
            app.debug = True

    def test_image_download_jpeg_non_debug(self):
        """Test JPEG image download uses X-Accel-Redirect in non-debug mode."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/images/test-bund-2020_0.jpg')
                assert response.status_code == 200
                assert response.headers['Content-Type'] == 'image/jpeg'
                assert response.headers['X-Accel-Redirect'] == '/internal-images/test-bund-2020_0.jpg'
                assert 'noindex' in response.headers.get('X-Robots-Tag', '')
        finally:
            app.debug = True

    def test_image_download_avif_non_debug(self):
        """Test AVIF image download uses X-Accel-Redirect with correct content type."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/images/test-bund-2020_0.avif')
                assert response.status_code == 200
                assert response.headers['Content-Type'] == 'image/avif'
                assert response.headers['X-Accel-Redirect'] == '/internal-images/test-bund-2020_0.avif'
                assert 'noindex' in response.headers.get('X-Robots-Tag', '')
        finally:
            app.debug = True


class TestSearchEdgeCases:
    """Test search edge cases for additional coverage."""

    def test_search_no_results_query(self):
        """Test search with a query that returns no results (covers empty snips path)."""
        from app import app
        with app.test_client() as client:
            response = client.get('/suche?q=xyznonexistentterm99999')
            assert response.status_code == 200


class TestAutocompleteEdgeCases:
    """Test autocomplete edge cases for additional coverage."""

    def test_autocomplete_three_words(self):
        """Test autocomplete with 3+ words to cover intersection loop."""
        from app import app
        with app.test_client() as client:
            response = client.get('/api/auto-complete?q=die+und+v')
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, list)

    def test_autocomplete_nonexistent_first_token(self):
        """Test autocomplete where first token has no matches (covers empty ids return)."""
        from app import app
        with app.test_client() as client:
            response = client.get('/api/auto-complete?q=xyznonexistent99+abc')
            assert response.status_code == 200
            assert response.get_json() == []
