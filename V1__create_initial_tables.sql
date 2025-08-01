-- Migração V1: Criação das tabelas iniciais
-- Data: 2025-01-08
-- Descrição: Cria as tabelas básicas do sistema de e-commerce

-- Tabela de clientes
CREATE TABLE clientes (
    id_cliente INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE
);

-- Tabela de produtos
CREATE TABLE produtos (
    id_produto INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    preco DECIMAL(10,2) NOT NULL,
    categoria VARCHAR(100),
    estoque INT DEFAULT 0,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE
);

-- Tabela de pedidos
CREATE TABLE pedidos (
    id_pedido INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL,
    data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pendente',
    valor_total DECIMAL(10,2) DEFAULT 0.00,
    observacoes TEXT,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
);

-- Tabela de itens de pedido
CREATE TABLE itens_pedido (
    id_item INT PRIMARY KEY AUTO_INCREMENT,
    id_pedido INT NOT NULL,
    id_produto INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido),
    FOREIGN KEY (id_produto) REFERENCES produtos(id_produto)
);

-- Tabela de logs de analytics
CREATE TABLE log_analytics (
    id_log INT PRIMARY KEY AUTO_INCREMENT,
    tipo_analise VARCHAR(100) NOT NULL,
    resultado TEXT,
    data_execucao DATETIME DEFAULT CURRENT_TIMESTAMP,
    tempo_execucao DECIMAL(8,3)
);

-- Índices para otimização
CREATE INDEX idx_clientes_email ON clientes(email);
CREATE INDEX idx_produtos_categoria ON produtos(categoria);
CREATE INDEX idx_pedidos_cliente ON pedidos(id_cliente);
CREATE INDEX idx_pedidos_data ON pedidos(data_pedido);
CREATE INDEX idx_itens_pedido ON itens_pedido(id_pedido);
CREATE INDEX idx_itens_produto ON itens_pedido(id_produto);
CREATE INDEX idx_analytics_tipo ON log_analytics(tipo_analise);
CREATE INDEX idx_analytics_data ON log_analytics(data_execucao);

