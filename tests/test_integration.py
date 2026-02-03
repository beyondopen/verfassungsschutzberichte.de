"""
Integration tests for verfassungsschutzberichte.de

These tests verify that HTTP endpoints work correctly after updates.
Run with: pytest tests/
"""

import pytest
import requests
import os


# Test configuration
BASE_URL = os.environ.get('TEST_BASE_URL', 'http://localhost:5000')
TIMEOUT = 10


class TestMainRoutes:
    """Test main pages load correctly"""

    def test_homepage_loads(self):
        """Test that homepage loads and returns 200"""
        response = requests.get(f'{BASE_URL}/', timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'Verfassungsschutzberichte' in response.text

    def test_reports_page_loads(self):
        """Test that reports overview page loads"""
        response = requests.get(f'{BASE_URL}/berichte', timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'Berichte' in response.text

    def test_search_page_loads(self):
        """Test that search page loads"""
        response = requests.get(f'{BASE_URL}/suche', timeout=TIMEOUT)
        assert response.status_code == 200

    def test_trends_page_loads(self):
        """Test that trends page loads with default parameters"""
        response = requests.get(f'{BASE_URL}/trends?q=nsu&q=raf', timeout=TIMEOUT)
        assert response.status_code == 200

    def test_regional_page_loads(self):
        """Test that regional page loads with default parameters"""
        response = requests.get(f'{BASE_URL}/regional?q=vvn-bda', timeout=TIMEOUT)
        assert response.status_code == 200

    def test_impressum_loads(self):
        """Test that impressum page loads"""
        response = requests.get(f'{BASE_URL}/impressum', timeout=TIMEOUT)
        assert response.status_code == 200


class TestSearchFunctionality:
    """Test search functionality"""

    def test_search_with_query(self):
        """Test that search works with a query"""
        response = requests.get(
            f'{BASE_URL}/suche',
            params={'q': 'nsu'},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        # Should have search results or "keine Ergebnisse"
        assert 'nsu' in response.text.lower() or 'ergebnis' in response.text.lower()

    def test_search_empty_query(self):
        """Test that search handles empty query"""
        response = requests.get(f'{BASE_URL}/suche', timeout=TIMEOUT)
        assert response.status_code == 200

    def test_stats_endpoint(self):
        """Test that stats endpoint returns JSON"""
        response = requests.get(
            f'{BASE_URL}/stats',
            params={'q': 'terror'},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/json'
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2  # Should return [query, data_dict]


class TestAPIEndpoints:
    """Test API endpoints"""

    def test_api_index(self):
        """Test API index endpoint"""
        response = requests.get(f'{BASE_URL}/api', timeout=TIMEOUT)
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/json'
        data = response.json()
        assert 'reports' in data
        assert 'total' in data
        assert isinstance(data['reports'], list)
        assert isinstance(data['total'], int)

    def test_api_autocomplete(self):
        """Test autocomplete endpoint"""
        response = requests.get(
            f'{BASE_URL}/api/auto-complete',
            params={'q': 'ter'},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/json'
        data = response.json()
        assert isinstance(data, list)

    def test_api_mentions(self):
        """Test mentions endpoint"""
        response = requests.get(
            f'{BASE_URL}/api/mentions',
            params={'q': 'nsu'},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/json'
        data = response.json()
        assert isinstance(data, dict)

    def test_api_mentions_csv(self):
        """Test mentions endpoint with CSV format"""
        response = requests.get(
            f'{BASE_URL}/api/mentions',
            params={'q': 'nsu', 'csv': '1'},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        assert 'text/plain' in response.headers['Content-Type']
        assert 'juris;year;count' in response.text


class TestImageServing:
    """Test image serving with AVIF support"""

    def test_jpeg_image_serves_with_correct_content_type(self):
        """Test that JPEG images are served with image/jpeg content type"""
        response = requests.get(
            f'{BASE_URL}/images/test-bund-2020_0.jpg',
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        assert 'image/jpeg' in response.headers.get('Content-Type', '')

    def test_avif_image_serves_with_correct_content_type(self):
        """Test that AVIF images are served with image/avif content type"""
        response = requests.get(
            f'{BASE_URL}/images/test-bund-2020_0.avif',
            timeout=TIMEOUT
        )
        # May 404 if AVIF not yet generated, but if it exists, content type must be correct
        if response.status_code == 200:
            assert 'image/avif' in response.headers.get('Content-Type', '')

    def test_details_page_uses_picture_element(self):
        """Test that report detail page uses picture element with AVIF source"""
        response = requests.get(f'{BASE_URL}/bund/2020', timeout=TIMEOUT)
        assert response.status_code == 200
        assert '<picture>' in response.text
        assert 'type="image/avif"' in response.text
        assert 'data-srcset=' in response.text
        assert '.avif' in response.text

    def test_search_results_use_picture_element(self):
        """Test that search results use picture element with AVIF source"""
        response = requests.get(
            f'{BASE_URL}/suche',
            params={'q': 'verfassungsschutz'},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        if 'Treffer' in response.text:
            assert '<picture>' in response.text
            assert 'type="image/avif"' in response.text


class TestStaticFiles:
    """Test static file serving"""

    def test_robots_txt(self):
        """Test that robots.txt is accessible"""
        response = requests.get(f'{BASE_URL}/robots.txt', timeout=TIMEOUT)
        assert response.status_code == 200


class TestBlogRoutes:
    """Test blog functionality"""

    def test_blog_index_loads(self):
        """Test that blog index page loads"""
        response = requests.get(f'{BASE_URL}/blog/', timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'Blog' in response.text

    def test_blog_post_launch(self):
        """Test that launch blog post loads"""
        response = requests.get(f'{BASE_URL}/blog/launch', timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'Pressemitteilung: Launch' in response.text

    def test_blog_post_36c3(self):
        """Test that 36C3 blog post loads"""
        response = requests.get(f'{BASE_URL}/blog/36c3', timeout=TIMEOUT)
        assert response.status_code == 200
        assert '36C3' in response.text or 'Chaos Computer Club' in response.text

    def test_blog_post_neue_berichte(self):
        """Test that neue-berichte-neues-feature blog post loads"""
        response = requests.get(f'{BASE_URL}/blog/neue-berichte-neues-feature', timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'Neue Berichte' in response.text

    def test_blog_post_urteil_im_anhang(self):
        """Test that urteil-im-anhang blog post loads with table"""
        response = requests.get(f'{BASE_URL}/blog/urteil-im-anhang', timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'Urteil im Anhang' in response.text
        assert '<table' in response.text  # Should contain table

    def test_blog_image_serves(self):
        """Test that blog images are served correctly"""
        response = requests.get(f'{BASE_URL}/blog/images/regional.png', timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'image' in response.headers.get('Content-Type', '')

    def test_blog_404_on_invalid_post(self):
        """Test that invalid blog post returns 404"""
        response = requests.get(
            f'{BASE_URL}/blog/this-post-does-not-exist',
            timeout=TIMEOUT,
            allow_redirects=False
        )
        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling"""

    def test_404_on_invalid_report(self):
        """Test that invalid report returns 404"""
        response = requests.get(
            f'{BASE_URL}/InvalidJurisdiction/9999',
            timeout=TIMEOUT,
            allow_redirects=False
        )
        assert response.status_code == 404

    def test_api_404_on_invalid_endpoint(self):
        """Test that invalid API endpoint returns 404"""
        response = requests.get(
            f'{BASE_URL}/api/InvalidJurisdiction/9999',
            timeout=TIMEOUT
        )
        assert response.status_code == 404


class TestSQLAlchemyCompatibility:
    """Test SQLAlchemy compatibility (important for Python upgrades)"""

    def test_database_queries_work(self):
        """Verify database queries work by checking API response"""
        response = requests.get(f'{BASE_URL}/api', timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        # If we get data, database queries are working
        assert data['total'] >= 0

    def test_search_vector_works(self):
        """Test that full-text search (TSVector) works"""
        response = requests.get(
            f'{BASE_URL}/suche',
            params={'q': 'verfassungsschutz'},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        # If we get a response, TSVector search is working


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
