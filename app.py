"""
Aplicação Flask para demonstrar integração com Amazon RDS
"""

from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__)

# Configuração do banco de dados
# Em produção, use variáveis de ambiente para credenciais
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'mysql+pymysql://admin:password@localhost:3306/exemplo_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar SQLAlchemy
db = SQLAlchemy(app)

# Importar modelos (assumindo que estão no mesmo diretório)
from ..database.models import Cliente, Produto, Pedido, ItemPedido, LogAnalytics

@app.route('/')
def home():
    """
    Endpoint raiz da API
    """
    return jsonify({
        'message': 'API Amazon RDS Demo',
        'version': '1.0.0',
        'endpoints': {
            'clientes': '/api/clientes',
            'produtos': '/api/produtos',
            'pedidos': '/api/pedidos',
            'analytics': '/api/analytics'
        }
    })

@app.route('/api/clientes', methods=['GET', 'POST'])
def clientes():
    """
    Gerenciar clientes
    """
    if request.method == 'GET':
        # Listar todos os clientes
        clientes = Cliente.query.filter_by(ativo=True).all()
        return jsonify([{
            'id': c.id_cliente,
            'nome': c.nome,
            'email': c.email,
            'telefone': c.telefone,
            'data_cadastro': c.data_cadastro.isoformat() if c.data_cadastro else None
        } for c in clientes])
    
    elif request.method == 'POST':
        # Criar novo cliente
        data = request.get_json()
        
        try:
            novo_cliente = Cliente(
                nome=data['nome'],
                email=data['email'],
                telefone=data.get('telefone')
            )
            
            db.session.add(novo_cliente)
            db.session.commit()
            
            return jsonify({
                'message': 'Cliente criado com sucesso',
                'id': novo_cliente.id_cliente
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@app.route('/api/produtos', methods=['GET', 'POST'])
def produtos():
    """
    Gerenciar produtos
    """
    if request.method == 'GET':
        # Listar produtos com filtros opcionais
        categoria = request.args.get('categoria')
        
        query = Produto.query.filter_by(ativo=True)
        if categoria:
            query = query.filter_by(categoria=categoria)
        
        produtos = query.all()
        
        return jsonify([{
            'id': p.id_produto,
            'nome': p.nome,
            'descricao': p.descricao,
            'preco': float(p.preco),
            'categoria': p.categoria,
            'estoque': p.estoque
        } for p in produtos])
    
    elif request.method == 'POST':
        # Criar novo produto
        data = request.get_json()
        
        try:
            novo_produto = Produto(
                nome=data['nome'],
                descricao=data.get('descricao'),
                preco=data['preco'],
                categoria=data.get('categoria'),
                estoque=data.get('estoque', 0)
            )
            
            db.session.add(novo_produto)
            db.session.commit()
            
            return jsonify({
                'message': 'Produto criado com sucesso',
                'id': novo_produto.id_produto
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@app.route('/api/pedidos', methods=['GET', 'POST'])
def pedidos():
    """
    Gerenciar pedidos
    """
    if request.method == 'GET':
        # Listar pedidos com informações do cliente
        pedidos = db.session.query(Pedido, Cliente).join(Cliente).all()
        
        return jsonify([{
            'id': p.id_pedido,
            'cliente': {
                'id': c.id_cliente,
                'nome': c.nome,
                'email': c.email
            },
            'data_pedido': p.data_pedido.isoformat() if p.data_pedido else None,
            'status': p.status,
            'valor_total': float(p.valor_total),
            'observacoes': p.observacoes
        } for p, c in pedidos])
    
    elif request.method == 'POST':
        # Criar novo pedido
        data = request.get_json()
        
        try:
            novo_pedido = Pedido(
                id_cliente=data['id_cliente'],
                status=data.get('status', 'pendente'),
                observacoes=data.get('observacoes')
            )
            
            db.session.add(novo_pedido)
            db.session.flush()  # Para obter o ID do pedido
            
            # Adicionar itens do pedido
            valor_total = 0
            for item_data in data.get('itens', []):
                produto = Produto.query.get(item_data['id_produto'])
                if not produto:
                    raise ValueError(f"Produto {item_data['id_produto']} não encontrado")
                
                subtotal = item_data['quantidade'] * produto.preco
                valor_total += subtotal
                
                item = ItemPedido(
                    id_pedido=novo_pedido.id_pedido,
                    id_produto=item_data['id_produto'],
                    quantidade=item_data['quantidade'],
                    preco_unitario=produto.preco,
                    subtotal=subtotal
                )
                
                db.session.add(item)
            
            # Atualizar valor total do pedido
            novo_pedido.valor_total = valor_total
            
            db.session.commit()
            
            return jsonify({
                'message': 'Pedido criado com sucesso',
                'id': novo_pedido.id_pedido,
                'valor_total': float(valor_total)
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@app.route('/api/analytics/vendas-diarias')
def analytics_vendas_diarias():
    """
    Análise de vendas diárias
    """
    try:
        # Query para vendas por dia
        query = """
        SELECT 
            DATE(data_pedido) as data,
            COUNT(*) as total_pedidos,
            SUM(valor_total) as total_vendas
        FROM pedidos 
        WHERE status != 'cancelado'
        GROUP BY DATE(data_pedido)
        ORDER BY data DESC
        LIMIT 30
        """
        
        start_time = datetime.now()
        result = db.session.execute(query)
        end_time = datetime.now()
        
        vendas = [{
            'data': row[0].isoformat() if row[0] else None,
            'total_pedidos': row[1],
            'total_vendas': float(row[2]) if row[2] else 0
        } for row in result]
        
        # Log da análise
        log_entry = LogAnalytics(
            tipo_analise='vendas_diarias',
            resultado=str(len(vendas)) + ' registros',
            tempo_execucao=(end_time - start_time).total_seconds()
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return jsonify({
            'vendas_diarias': vendas,
            'total_registros': len(vendas),
            'tempo_execucao': (end_time - start_time).total_seconds()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/produtos-populares')
def analytics_produtos_populares():
    """
    Análise de produtos mais vendidos
    """
    try:
        # Query para produtos mais vendidos
        query = """
        SELECT 
            p.nome,
            p.categoria,
            SUM(ip.quantidade) as total_vendido,
            SUM(ip.subtotal) as receita_total
        FROM produtos p
        JOIN itens_pedido ip ON p.id_produto = ip.id_produto
        JOIN pedidos ped ON ip.id_pedido = ped.id_pedido
        WHERE ped.status != 'cancelado'
        GROUP BY p.id_produto, p.nome, p.categoria
        ORDER BY total_vendido DESC
        LIMIT 10
        """
        
        start_time = datetime.now()
        result = db.session.execute(query)
        end_time = datetime.now()
        
        produtos = [{
            'nome': row[0],
            'categoria': row[1],
            'total_vendido': row[2],
            'receita_total': float(row[3]) if row[3] else 0
        } for row in result]
        
        # Log da análise
        log_entry = LogAnalytics(
            tipo_analise='produtos_populares',
            resultado=str(len(produtos)) + ' produtos',
            tempo_execucao=(end_time - start_time).total_seconds()
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return jsonify({
            'produtos_populares': produtos,
            'tempo_execucao': (end_time - start_time).total_seconds()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """
    Endpoint de health check para monitoramento
    """
    try:
        # Testar conexão com o banco
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    # Criar tabelas se não existirem
    with app.app_context():
        db.create_all()
    
    # Executar aplicação
    app.run(host='0.0.0.0', port=5000, debug=True)

