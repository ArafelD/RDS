"""
Módulo de conexão com Amazon RDS
Este módulo gerencia a conexão com o banco de dados MySQL no Amazon RDS
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base para os modelos SQLAlchemy
Base = declarative_base()

class RDSConnection:
    """
    Classe para gerenciar conexões com Amazon RDS
    """
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        
    def create_connection(self, host, port, database, username, password):
        """
        Cria uma conexão com o Amazon RDS
        
        Args:
            host (str): Endpoint do RDS
            port (int): Porta do banco de dados
            database (str): Nome do banco de dados
            username (str): Nome do usuário
            password (str): Senha do usuário
        """
        try:
            # String de conexão para MySQL
            connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
            
            # Criar engine SQLAlchemy
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,  # Verifica conexões antes de usar
                pool_recycle=3600,   # Recicla conexões a cada hora
                echo=False           # Set True para debug SQL
            )
            
            # Criar factory de sessões
            self.session_factory = sessionmaker(bind=self.engine)
            
            logger.info(f"Conexão estabelecida com sucesso: {host}:{port}/{database}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao conectar com o RDS: {str(e)}")
            return False
    
    def get_session(self):
        """
        Retorna uma nova sessão do banco de dados
        """
        if self.session_factory:
            return self.session_factory()
        else:
            raise Exception("Conexão não estabelecida. Execute create_connection() primeiro.")
    
    def test_connection(self):
        """
        Testa a conexão com o banco de dados
        """
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                logger.info("Teste de conexão bem-sucedido!")
                return True
        except Exception as e:
            logger.error(f"Falha no teste de conexão: {str(e)}")
            return False
    
    def close_connection(self):
        """
        Fecha a conexão com o banco de dados
        """
        if self.engine:
            self.engine.dispose()
            logger.info("Conexão fechada.")

# Instância global da conexão
rds_connection = RDSConnection()

def get_db_session():
    """
    Função utilitária para obter uma sessão do banco de dados
    """
    return rds_connection.get_session()

# Exemplo de uso
if __name__ == "__main__":
    # Configurações de exemplo (substitua pelos seus valores reais)
    config = {
        'host': 'seu-rds-endpoint.region.rds.amazonaws.com',
        'port': 3306,
        'database': 'exemplo_db',
        'username': 'admin',
        'password': 'sua_senha_segura'
    }
    
    # Criar conexão
    if rds_connection.create_connection(**config):
        # Testar conexão
        rds_connection.test_connection()
        
        # Fechar conexão
        rds_connection.close_connection()

