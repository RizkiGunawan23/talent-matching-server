from typing import Dict, List, Optional, Any
from neo4j import GraphDatabase, Driver
from django.conf import settings
import os
from urllib.parse import urlparse


class BaseNeo4jService:
    """
    Base service class untuk semua Neo4j operations
    """
    _driver = None

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._parse_connection_config()
            self.initialized = True

    def _parse_connection_config(self):
        """Parse Neo4j connection from environment variables"""
        neo4j_url = getattr(settings, 'NEO4J_BOLT_URL', None) or os.getenv('NEO4J_BOLT_URL', 'bolt://localhost:7687')
        
        parsed = urlparse(neo4j_url)
        
        if parsed.username and parsed.password:
            self.user = parsed.username
            self.password = parsed.password
            self.uri = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 7687}"
        else:
            self.uri = getattr(settings, 'NEO4J_URI', 'bolt://localhost:7687')
            self.user = getattr(settings, 'NEO4J_USER', 'neo4j')
            self.password = getattr(settings, 'NEO4J_PASSWORD', '12345678')

    def get_driver(self) -> Driver:
        """Get Neo4j driver instance (singleton pattern)"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        return self._driver

    def close_driver(self):
        """Close the driver connection"""
        if self._driver:
            self._driver.close()
            self._driver = None

    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """Execute a Cypher query and return results as list of dictionaries"""
        driver = self.get_driver()
        
        try:
            with driver.session() as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            raise

    def execute_write_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """Execute a write query (CREATE, UPDATE, DELETE) in a write transaction"""
        driver = self.get_driver()
        
        try:
            with driver.session() as session:
                result = session.execute_write(
                    lambda tx: list(tx.run(query, parameters or {}))
                )
                return [dict(record) for record in result]
        except Exception as e:
            print(f"Error executing write query: {str(e)}")
            raise

    def __del__(self):
        """Cleanup when object is destroyed"""
        self.close_driver()