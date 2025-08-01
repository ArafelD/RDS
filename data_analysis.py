"""
Módulo de análise de dados para Amazon RDS
Demonstra como realizar análises avançadas usando pandas e SQLAlchemy
"""

import pandas as pd
import numpy as np
from sqlalchemy import text
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from ..database.connection import get_db_session
from ..database.models import LogAnalytics
import json

class RDSAnalytics:
    """
    Classe para realizar análises de dados no Amazon RDS
    """
    
    def __init__(self):
        self.session = None
        
    def connect(self):
        """
        Conecta com o banco de dados
        """
        try:
            self.session = get_db_session()
            return True
        except Exception as e:
            print(f"Erro ao conectar: {e}")
            return False
    
    def execute_query_to_dataframe(self, query, params=None):
        """
        Executa uma query SQL e retorna um DataFrame pandas
        """
        if not self.session:
            raise Exception("Não conectado ao banco de dados")
        
        try:
            if params:
                result = self.session.execute(text(query), params)
            else:
                result = self.session.execute(text(query))
            
            # Converter para DataFrame
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df
        except Exception as e:
            print(f"Erro ao executar query: {e}")
            return None
    
    def analise_vendas_por_periodo(self, dias=30):
        """
        Análise de vendas por período
        """
        query = """
        SELECT 
            DATE(data_pedido) as data,
            COUNT(*) as total_pedidos,
            SUM(valor_total) as total_vendas,
            AVG(valor_total) as ticket_medio
        FROM pedidos 
        WHERE data_pedido >= DATE_SUB(CURDATE(), INTERVAL :dias DAY)
        AND status != 'cancelado'
        GROUP BY DATE(data_pedido)
        ORDER BY data
        """
        
        start_time = datetime.now()
        df = self.execute_query_to_dataframe(query, {'dias': dias})
        end_time = datetime.now()
        
        if df is not None and not df.empty:
            # Converter coluna de data
            df['data'] = pd.to_datetime(df['data'])
            
            # Calcular métricas
            total_vendas = df['total_vendas'].sum()
            total_pedidos = df['total_pedidos'].sum()
            ticket_medio_geral = total_vendas / total_pedidos if total_pedidos > 0 else 0
            
            # Tendência de crescimento
            if len(df) > 1:
                crescimento = ((df['total_vendas'].iloc[-1] - df['total_vendas'].iloc[0]) / 
                              df['total_vendas'].iloc[0] * 100) if df['total_vendas'].iloc[0] > 0 else 0
            else:
                crescimento = 0
            
            resultado = {
                'periodo_dias': dias,
                'total_vendas': float(total_vendas),
                'total_pedidos': int(total_pedidos),
                'ticket_medio_geral': float(ticket_medio_geral),
                'crescimento_percentual': float(crescimento),
                'dados_diarios': df.to_dict('records')
            }
            
            # Log da análise
            self._log_analise('vendas_por_periodo', resultado, 
                            (end_time - start_time).total_seconds())
            
            return resultado
        
        return None
    
    def analise_produtos_performance(self):
        """
        Análise de performance de produtos
        """
        query = """
        SELECT 
            p.id_produto,
            p.nome,
            p.categoria,
            p.preco,
            p.estoque,
            COALESCE(SUM(ip.quantidade), 0) as total_vendido,
            COALESCE(SUM(ip.subtotal), 0) as receita_total,
            COALESCE(COUNT(DISTINCT ip.id_pedido), 0) as pedidos_com_produto,
            COALESCE(AVG(ip.quantidade), 0) as quantidade_media_por_pedido
        FROM produtos p
        LEFT JOIN itens_pedido ip ON p.id_produto = ip.id_produto
        LEFT JOIN pedidos ped ON ip.id_pedido = ped.id_pedido AND ped.status != 'cancelado'
        WHERE p.ativo = 1
        GROUP BY p.id_produto, p.nome, p.categoria, p.preco, p.estoque
        ORDER BY receita_total DESC
        """
        
        start_time = datetime.now()
        df = self.execute_query_to_dataframe(query)
        end_time = datetime.now()
        
        if df is not None and not df.empty:
            # Calcular métricas adicionais
            df['margem_contribuicao'] = df['receita_total'] / df['receita_total'].sum() * 100
            df['giro_estoque'] = df['total_vendido'] / df['estoque'].replace(0, 1)  # Evitar divisão por zero
            df['performance_score'] = (df['receita_total'] * 0.4 + 
                                     df['total_vendido'] * 0.3 + 
                                     df['pedidos_com_produto'] * 0.3)
            
            # Top performers
            top_receita = df.nlargest(5, 'receita_total')[['nome', 'receita_total']].to_dict('records')
            top_quantidade = df.nlargest(5, 'total_vendido')[['nome', 'total_vendido']].to_dict('records')
            
            resultado = {
                'total_produtos': len(df),
                'receita_total_geral': float(df['receita_total'].sum()),
                'top_produtos_receita': top_receita,
                'top_produtos_quantidade': top_quantidade,
                'produtos_sem_vendas': int(len(df[df['total_vendido'] == 0])),
                'dados_completos': df.to_dict('records')
            }
            
            # Log da análise
            self._log_analise('produtos_performance', resultado, 
                            (end_time - start_time).total_seconds())
            
            return resultado
        
        return None
    
    def analise_clientes_comportamento(self):
        """
        Análise de comportamento de clientes
        """
        query = """
        SELECT 
            c.id_cliente,
            c.nome,
            c.email,
            c.data_cadastro,
            COUNT(p.id_pedido) as total_pedidos,
            COALESCE(SUM(p.valor_total), 0) as valor_total_gasto,
            COALESCE(AVG(p.valor_total), 0) as ticket_medio,
            MAX(p.data_pedido) as ultimo_pedido,
            DATEDIFF(CURDATE(), MAX(p.data_pedido)) as dias_desde_ultimo_pedido
        FROM clientes c
        LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente AND p.status != 'cancelado'
        WHERE c.ativo = 1
        GROUP BY c.id_cliente, c.nome, c.email, c.data_cadastro
        ORDER BY valor_total_gasto DESC
        """
        
        start_time = datetime.now()
        df = self.execute_query_to_dataframe(query)
        end_time = datetime.now()
        
        if df is not None and not df.empty:
            # Converter datas
            df['data_cadastro'] = pd.to_datetime(df['data_cadastro'])
            df['ultimo_pedido'] = pd.to_datetime(df['ultimo_pedido'])
            
            # Segmentação de clientes
            df['segmento'] = 'Novo'  # Default
            df.loc[(df['total_pedidos'] >= 2) & (df['total_pedidos'] < 5), 'segmento'] = 'Regular'
            df.loc[df['total_pedidos'] >= 5, 'segmento'] = 'VIP'
            df.loc[df['dias_desde_ultimo_pedido'] > 90, 'segmento'] = 'Inativo'
            
            # Métricas por segmento
            segmentos = df.groupby('segmento').agg({
                'id_cliente': 'count',
                'valor_total_gasto': ['sum', 'mean'],
                'total_pedidos': 'mean',
                'ticket_medio': 'mean'
            }).round(2)
            
            resultado = {
                'total_clientes': len(df),
                'clientes_ativos': int(len(df[df['total_pedidos'] > 0])),
                'valor_total_base': float(df['valor_total_gasto'].sum()),
                'ticket_medio_geral': float(df[df['total_pedidos'] > 0]['ticket_medio'].mean()),
                'segmentacao': segmentos.to_dict(),
                'top_clientes': df.nlargest(10, 'valor_total_gasto')[
                    ['nome', 'email', 'total_pedidos', 'valor_total_gasto']
                ].to_dict('records')
            }
            
            # Log da análise
            self._log_analise('clientes_comportamento', resultado, 
                            (end_time - start_time).total_seconds())
            
            return resultado
        
        return None
    
    def previsao_vendas_simples(self, dias_previsao=7):
        """
        Previsão simples de vendas usando média móvel
        """
        query = """
        SELECT 
            DATE(data_pedido) as data,
            SUM(valor_total) as total_vendas
        FROM pedidos 
        WHERE data_pedido >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        AND status != 'cancelado'
        GROUP BY DATE(data_pedido)
        ORDER BY data
        """
        
        start_time = datetime.now()
        df = self.execute_query_to_dataframe(query)
        end_time = datetime.now()
        
        if df is not None and not df.empty and len(df) >= 7:
            df['data'] = pd.to_datetime(df['data'])
            df = df.sort_values('data')
            
            # Calcular média móvel de 7 dias
            df['media_movel_7'] = df['total_vendas'].rolling(window=7).mean()
            
            # Previsão simples baseada na média dos últimos 7 dias
            media_ultimos_7_dias = df['total_vendas'].tail(7).mean()
            
            # Gerar previsões
            ultima_data = df['data'].max()
            previsoes = []
            
            for i in range(1, dias_previsao + 1):
                data_previsao = ultima_data + timedelta(days=i)
                # Adicionar um pouco de variação baseada no desvio padrão
                variacao = np.random.normal(0, df['total_vendas'].std() * 0.1)
                valor_previsto = max(0, media_ultimos_7_dias + variacao)
                
                previsoes.append({
                    'data': data_previsao.strftime('%Y-%m-%d'),
                    'valor_previsto': float(valor_previsto),
                    'confianca': 'baixa'  # Método simples tem baixa confiança
                })
            
            resultado = {
                'dados_historicos': df.to_dict('records'),
                'media_ultimos_7_dias': float(media_ultimos_7_dias),
                'previsoes': previsoes,
                'metodo': 'media_movel_simples',
                'dias_previsao': dias_previsao
            }
            
            # Log da análise
            self._log_analise('previsao_vendas', resultado, 
                            (end_time - start_time).total_seconds())
            
            return resultado
        
        return None
    
    def _log_analise(self, tipo_analise, resultado, tempo_execucao):
        """
        Registra a execução de uma análise no banco de dados
        """
        try:
            log_entry = LogAnalytics(
                tipo_analise=tipo_analise,
                resultado=json.dumps(resultado, default=str)[:1000],  # Limitar tamanho
                tempo_execucao=tempo_execucao
            )
            self.session.add(log_entry)
            self.session.commit()
        except Exception as e:
            print(f"Erro ao registrar log: {e}")
    
    def gerar_relatorio_completo(self):
        """
        Gera um relatório completo com todas as análises
        """
        relatorio = {
            'data_geracao': datetime.now().isoformat(),
            'vendas': self.analise_vendas_por_periodo(30),
            'produtos': self.analise_produtos_performance(),
            'clientes': self.analise_clientes_comportamento(),
            'previsao': self.previsao_vendas_simples(7)
        }
        
        return relatorio
    
    def close(self):
        """
        Fecha a conexão com o banco de dados
        """
        if self.session:
            self.session.close()

# Exemplo de uso
if __name__ == "__main__":
    analytics = RDSAnalytics()
    
    if analytics.connect():
        print("Conectado ao banco de dados!")
        
        # Executar análises
        print("\n=== Análise de Vendas ===")
        vendas = analytics.analise_vendas_por_periodo(30)
        if vendas:
            print(f"Total de vendas (30 dias): R$ {vendas['total_vendas']:.2f}")
            print(f"Total de pedidos: {vendas['total_pedidos']}")
            print(f"Ticket médio: R$ {vendas['ticket_medio_geral']:.2f}")
        
        print("\n=== Análise de Produtos ===")
        produtos = analytics.analise_produtos_performance()
        if produtos:
            print(f"Total de produtos: {produtos['total_produtos']}")
            print(f"Receita total: R$ {produtos['receita_total_geral']:.2f}")
            print(f"Produtos sem vendas: {produtos['produtos_sem_vendas']}")
        
        print("\n=== Análise de Clientes ===")
        clientes = analytics.analise_clientes_comportamento()
        if clientes:
            print(f"Total de clientes: {clientes['total_clientes']}")
            print(f"Clientes ativos: {clientes['clientes_ativos']}")
            print(f"Ticket médio geral: R$ {clientes['ticket_medio_geral']:.2f}")
        
        analytics.close()
    else:
        print("Falha ao conectar com o banco de dados!")

