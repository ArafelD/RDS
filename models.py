"""
Modelos de dados para o projeto Amazon RDS
Define as tabelas e relacionamentos do banco de dados
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .connection import Base

class Cliente(Base):
    """
    Modelo para a tabela de clientes
    """
    __tablename__ = 'clientes'
    
    id_cliente = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    telefone = Column(String(20))
    data_cadastro = Column(DateTime, default=datetime.utcnow)
    ativo = Column(Boolean, default=True)
    
    # Relacionamento com pedidos
    pedidos = relationship("Pedido", back_populates="cliente")
    
    def __repr__(self):
        return f"<Cliente(id={self.id_cliente}, nome='{self.nome}', email='{self.email}')>"

class Produto(Base):
    """
    Modelo para a tabela de produtos
    """
    __tablename__ = 'produtos'
    
    id_produto = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text)
    preco = Column(Float, nullable=False)
    categoria = Column(String(100))
    estoque = Column(Integer, default=0)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    ativo = Column(Boolean, default=True)
    
    # Relacionamento com itens de pedido
    itens_pedido = relationship("ItemPedido", back_populates="produto")
    
    def __repr__(self):
        return f"<Produto(id={self.id_produto}, nome='{self.nome}', preco={self.preco})>"

class Pedido(Base):
    """
    Modelo para a tabela de pedidos
    """
    __tablename__ = 'pedidos'
    
    id_pedido = Column(Integer, primary_key=True, autoincrement=True)
    id_cliente = Column(Integer, ForeignKey('clientes.id_cliente'), nullable=False)
    data_pedido = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='pendente')  # pendente, processando, enviado, entregue, cancelado
    valor_total = Column(Float, default=0.0)
    observacoes = Column(Text)
    
    # Relacionamentos
    cliente = relationship("Cliente", back_populates="pedidos")
    itens = relationship("ItemPedido", back_populates="pedido")
    
    def __repr__(self):
        return f"<Pedido(id={self.id_pedido}, cliente_id={self.id_cliente}, valor_total={self.valor_total})>"

class ItemPedido(Base):
    """
    Modelo para a tabela de itens de pedido (relacionamento many-to-many entre Pedido e Produto)
    """
    __tablename__ = 'itens_pedido'
    
    id_item = Column(Integer, primary_key=True, autoincrement=True)
    id_pedido = Column(Integer, ForeignKey('pedidos.id_pedido'), nullable=False)
    id_produto = Column(Integer, ForeignKey('produtos.id_produto'), nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    
    # Relacionamentos
    pedido = relationship("Pedido", back_populates="itens")
    produto = relationship("Produto", back_populates="itens_pedido")
    
    def __repr__(self):
        return f"<ItemPedido(pedido_id={self.id_pedido}, produto_id={self.id_produto}, qtd={self.quantidade})>"

class LogAnalytics(Base):
    """
    Modelo para armazenar logs de análises e métricas
    """
    __tablename__ = 'log_analytics'
    
    id_log = Column(Integer, primary_key=True, autoincrement=True)
    tipo_analise = Column(String(100), nullable=False)  # vendas_diarias, produtos_populares, etc.
    resultado = Column(Text)  # JSON com os resultados da análise
    data_execucao = Column(DateTime, default=datetime.utcnow)
    tempo_execucao = Column(Float)  # tempo em segundos
    
    def __repr__(self):
        return f"<LogAnalytics(id={self.id_log}, tipo='{self.tipo_analise}', data={self.data_execucao})>"

# Funções utilitárias para trabalhar com os modelos

def criar_tabelas(engine):
    """
    Cria todas as tabelas no banco de dados
    """
    Base.metadata.create_all(engine)
    print("Tabelas criadas com sucesso!")

def inserir_dados_exemplo(session):
    """
    Insere dados de exemplo para testes
    """
    # Criar clientes de exemplo
    clientes = [
        Cliente(nome="Ana Silva", email="ana.silva@email.com", telefone="11999999999"),
        Cliente(nome="João Santos", email="joao.santos@email.com", telefone="11888888888"),
        Cliente(nome="Maria Oliveira", email="maria.oliveira@email.com", telefone="11777777777")
    ]
    
    # Criar produtos de exemplo
    produtos = [
        Produto(nome="Notebook Dell", descricao="Notebook Dell Inspiron 15", preco=2500.00, categoria="Eletrônicos", estoque=10),
        Produto(nome="Mouse Logitech", descricao="Mouse sem fio Logitech", preco=89.90, categoria="Acessórios", estoque=50),
        Produto(nome="Teclado Mecânico", descricao="Teclado mecânico RGB", preco=299.99, categoria="Acessórios", estoque=25),
        Produto(nome="Monitor 24\"", descricao="Monitor LED 24 polegadas", preco=899.00, categoria="Eletrônicos", estoque=15)
    ]
    
    # Adicionar à sessão
    session.add_all(clientes)
    session.add_all(produtos)
    session.commit()
    
    # Criar pedidos de exemplo
    pedidos = [
        Pedido(id_cliente=1, status="entregue", valor_total=2589.90),
        Pedido(id_cliente=2, status="processando", valor_total=1198.99),
        Pedido(id_cliente=1, status="pendente", valor_total=389.89)
    ]
    
    session.add_all(pedidos)
    session.commit()
    
    # Criar itens de pedido
    itens = [
        ItemPedido(id_pedido=1, id_produto=1, quantidade=1, preco_unitario=2500.00, subtotal=2500.00),
        ItemPedido(id_pedido=1, id_produto=2, quantidade=1, preco_unitario=89.90, subtotal=89.90),
        ItemPedido(id_pedido=2, id_produto=4, quantidade=1, preco_unitario=899.00, subtotal=899.00),
        ItemPedido(id_pedido=2, id_produto=3, quantidade=1, preco_unitario=299.99, subtotal=299.99),
        ItemPedido(id_pedido=3, id_produto=2, quantidade=2, preco_unitario=89.90, subtotal=179.80),
        ItemPedido(id_pedido=3, id_produto=3, quantidade=1, preco_unitario=299.99, subtotal=299.99)
    ]
    
    session.add_all(itens)
    session.commit()
    
    print("Dados de exemplo inseridos com sucesso!")

if __name__ == "__main__":
    from .connection import rds_connection
    
    # Exemplo de uso dos modelos
    print("Modelos de dados definidos:")
    print("- Cliente")
    print("- Produto") 
    print("- Pedido")
    print("- ItemPedido")
    print("- LogAnalytics")

