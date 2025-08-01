"""
Módulo de integração com Machine Learning para Amazon RDS
Demonstra como usar dados do RDS para treinar modelos de ML
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, accuracy_score, classification_report
import joblib
import os
from datetime import datetime, timedelta
from ..database.connection import get_db_session
from ..database.models import LogAnalytics
import json

class RDSMLIntegration:
    """
    Classe para integração de Machine Learning com dados do Amazon RDS
    """
    
    def __init__(self):
        self.session = None
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        
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
    
    def preparar_dados_previsao_vendas(self, dias_historico=90):
        """
        Prepara dados para previsão de vendas
        """
        query = """
        SELECT 
            DATE(data_pedido) as data,
            COUNT(*) as total_pedidos,
            SUM(valor_total) as total_vendas,
            AVG(valor_total) as ticket_medio,
            DAYOFWEEK(data_pedido) as dia_semana,
            DAY(data_pedido) as dia_mes,
            MONTH(data_pedido) as mes,
            YEAR(data_pedido) as ano
        FROM pedidos 
        WHERE data_pedido >= DATE_SUB(CURDATE(), INTERVAL :dias DAY)
        AND status != 'cancelado'
        GROUP BY DATE(data_pedido)
        ORDER BY data
        """
        
        result = self.session.execute(query, {'dias': dias_historico})
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        if not df.empty:
            # Converter data
            df['data'] = pd.to_datetime(df['data'])
            
            # Criar features temporais
            df['dia_semana'] = df['data'].dt.dayofweek
            df['dia_mes'] = df['data'].dt.day
            df['mes'] = df['data'].dt.month
            df['trimestre'] = df['data'].dt.quarter
            df['semana_ano'] = df['data'].dt.isocalendar().week
            
            # Features de lag (valores dos dias anteriores)
            df['vendas_lag_1'] = df['total_vendas'].shift(1)
            df['vendas_lag_7'] = df['total_vendas'].shift(7)
            df['pedidos_lag_1'] = df['total_pedidos'].shift(1)
            
            # Médias móveis
            df['media_movel_7'] = df['total_vendas'].rolling(window=7).mean()
            df['media_movel_14'] = df['total_vendas'].rolling(window=14).mean()
            
            # Remover linhas com NaN (devido aos lags)
            df = df.dropna()
            
            return df
        
        return None
    
    def treinar_modelo_previsao_vendas(self):
        """
        Treina um modelo para prever vendas diárias
        """
        print("Preparando dados para previsão de vendas...")
        df = self.preparar_dados_previsao_vendas()
        
        if df is None or len(df) < 30:
            print("Dados insuficientes para treinar o modelo")
            return None
        
        # Features para o modelo
        features = [
            'total_pedidos', 'ticket_medio', 'dia_semana', 'dia_mes', 'mes', 
            'trimestre', 'semana_ano', 'vendas_lag_1', 'vendas_lag_7', 
            'pedidos_lag_1', 'media_movel_7', 'media_movel_14'
        ]
        
        X = df[features]
        y = df['total_vendas']
        
        # Dividir dados em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )
        
        # Normalizar features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Treinar modelo Random Forest
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train_scaled, y_train)
        
        # Avaliar modelo
        y_pred = model.predict(X_test_scaled)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        
        # Importância das features
        feature_importance = pd.DataFrame({
            'feature': features,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Salvar modelo e scaler
        self.models['previsao_vendas'] = model
        self.scalers['previsao_vendas'] = scaler
        
        resultado = {
            'modelo': 'RandomForestRegressor',
            'rmse': float(rmse),
            'mse': float(mse),
            'tamanho_treino': len(X_train),
            'tamanho_teste': len(X_test),
            'feature_importance': feature_importance.to_dict('records'),
            'data_treino': datetime.now().isoformat()
        }
        
        print(f"Modelo treinado com sucesso! RMSE: {rmse:.2f}")
        return resultado
    
    def prever_vendas_futuras(self, dias_futuro=7):
        """
        Faz previsões de vendas para os próximos dias
        """
        if 'previsao_vendas' not in self.models:
            print("Modelo de previsão não encontrado. Treine o modelo primeiro.")
            return None
        
        model = self.models['previsao_vendas']
        scaler = self.scalers['previsao_vendas']
        
        # Obter dados mais recentes
        df = self.preparar_dados_previsao_vendas(30)
        if df is None or df.empty:
            return None
        
        # Última linha de dados
        ultima_linha = df.iloc[-1].copy()
        previsoes = []
        
        for i in range(dias_futuro):
            # Preparar features para previsão
            data_futura = ultima_linha['data'] + timedelta(days=i+1)
            
            # Features temporais
            features_futuras = {
                'total_pedidos': ultima_linha['total_pedidos'],  # Usar último valor conhecido
                'ticket_medio': ultima_linha['ticket_medio'],
                'dia_semana': data_futura.dayofweek,
                'dia_mes': data_futura.day,
                'mes': data_futura.month,
                'trimestre': (data_futura.month - 1) // 3 + 1,
                'semana_ano': data_futura.isocalendar()[1],
                'vendas_lag_1': ultima_linha['total_vendas'],
                'vendas_lag_7': df.iloc[-7]['total_vendas'] if len(df) >= 7 else ultima_linha['total_vendas'],
                'pedidos_lag_1': ultima_linha['total_pedidos'],
                'media_movel_7': df['total_vendas'].tail(7).mean(),
                'media_movel_14': df['total_vendas'].tail(14).mean()
            }
            
            # Converter para array
            X_pred = np.array([list(features_futuras.values())])
            X_pred_scaled = scaler.transform(X_pred)
            
            # Fazer previsão
            vendas_previstas = model.predict(X_pred_scaled)[0]
            
            previsoes.append({
                'data': data_futura.strftime('%Y-%m-%d'),
                'vendas_previstas': float(max(0, vendas_previstas)),  # Não pode ser negativo
                'dia_semana': data_futura.strftime('%A'),
                'confianca': 'media'
            })
            
            # Atualizar última linha para próxima iteração
            ultima_linha['total_vendas'] = vendas_previstas
        
        return previsoes
    
    def preparar_dados_segmentacao_clientes(self):
        """
        Prepara dados para segmentação de clientes
        """
        query = """
        SELECT 
            c.id_cliente,
            c.nome,
            DATEDIFF(CURDATE(), c.data_cadastro) as dias_desde_cadastro,
            COUNT(p.id_pedido) as total_pedidos,
            COALESCE(SUM(p.valor_total), 0) as valor_total_gasto,
            COALESCE(AVG(p.valor_total), 0) as ticket_medio,
            COALESCE(MAX(p.data_pedido), c.data_cadastro) as ultimo_pedido,
            DATEDIFF(CURDATE(), COALESCE(MAX(p.data_pedido), c.data_cadastro)) as dias_desde_ultimo_pedido,
            COUNT(DISTINCT DATE(p.data_pedido)) as dias_com_compras
        FROM clientes c
        LEFT JOIN pedidos p ON c.id_cliente = p.id_cliente AND p.status != 'cancelado'
        WHERE c.ativo = 1
        GROUP BY c.id_cliente, c.nome, c.data_cadastro
        """
        
        result = self.session.execute(query)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        if not df.empty:
            # Calcular features adicionais
            df['frequencia_compra'] = df['total_pedidos'] / (df['dias_desde_cadastro'] + 1) * 30  # Pedidos por mês
            df['valor_por_dia_ativo'] = df['valor_total_gasto'] / (df['dias_com_compras'] + 1)
            df['recencia_score'] = 1 / (df['dias_desde_ultimo_pedido'] + 1)  # Quanto menor o tempo, maior o score
            
            return df
        
        return None
    
    def segmentar_clientes_rfm(self):
        """
        Segmenta clientes usando análise RFM (Recency, Frequency, Monetary)
        """
        print("Preparando dados para segmentação RFM...")
        df = self.preparar_dados_segmentacao_clientes()
        
        if df is None or df.empty:
            print("Dados insuficientes para segmentação")
            return None
        
        # Calcular scores RFM (1-5, onde 5 é melhor)
        df['R_score'] = pd.qcut(df['dias_desde_ultimo_pedido'], 5, labels=[5,4,3,2,1])
        df['F_score'] = pd.qcut(df['total_pedidos'].rank(method='first'), 5, labels=[1,2,3,4,5])
        df['M_score'] = pd.qcut(df['valor_total_gasto'], 5, labels=[1,2,3,4,5])
        
        # Converter para numérico
        df['R_score'] = df['R_score'].astype(int)
        df['F_score'] = df['F_score'].astype(int)
        df['M_score'] = df['M_score'].astype(int)
        
        # Criar score RFM combinado
        df['RFM_score'] = df['R_score'].astype(str) + df['F_score'].astype(str) + df['M_score'].astype(str)
        
        # Definir segmentos baseados no score RFM
        def definir_segmento(row):
            score = row['RFM_score']
            r, f, m = int(score[0]), int(score[1]), int(score[2])
            
            if r >= 4 and f >= 4 and m >= 4:
                return 'Champions'
            elif r >= 3 and f >= 3 and m >= 3:
                return 'Loyal Customers'
            elif r >= 4 and f <= 2:
                return 'New Customers'
            elif r <= 2 and f >= 3:
                return 'At Risk'
            elif r <= 2 and f <= 2:
                return 'Lost Customers'
            else:
                return 'Regular Customers'
        
        df['segmento'] = df.apply(definir_segmento, axis=1)
        
        # Estatísticas por segmento
        segmentos_stats = df.groupby('segmento').agg({
            'id_cliente': 'count',
            'valor_total_gasto': ['sum', 'mean'],
            'total_pedidos': 'mean',
            'ticket_medio': 'mean',
            'dias_desde_ultimo_pedido': 'mean'
        }).round(2)
        
        resultado = {
            'total_clientes': len(df),
            'segmentos_stats': segmentos_stats.to_dict(),
            'distribuicao_segmentos': df['segmento'].value_counts().to_dict(),
            'clientes_segmentados': df[['id_cliente', 'nome', 'segmento', 'RFM_score', 
                                      'valor_total_gasto', 'total_pedidos']].to_dict('records')
        }
        
        return resultado
    
    def detectar_anomalias_vendas(self, janela_dias=30):
        """
        Detecta anomalias nas vendas usando métodos estatísticos
        """
        query = """
        SELECT 
            DATE(data_pedido) as data,
            SUM(valor_total) as total_vendas,
            COUNT(*) as total_pedidos
        FROM pedidos 
        WHERE data_pedido >= DATE_SUB(CURDATE(), INTERVAL :dias DAY)
        AND status != 'cancelado'
        GROUP BY DATE(data_pedido)
        ORDER BY data
        """
        
        result = self.session.execute(query, {'dias': janela_dias})
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        if df is None or len(df) < 7:
            return None
        
        # Calcular estatísticas
        media = df['total_vendas'].mean()
        desvio = df['total_vendas'].std()
        
        # Definir limites para anomalias (2 desvios padrão)
        limite_superior = media + (2 * desvio)
        limite_inferior = max(0, media - (2 * desvio))
        
        # Identificar anomalias
        df['anomalia'] = (df['total_vendas'] > limite_superior) | (df['total_vendas'] < limite_inferior)
        df['tipo_anomalia'] = 'normal'
        df.loc[df['total_vendas'] > limite_superior, 'tipo_anomalia'] = 'acima_normal'
        df.loc[df['total_vendas'] < limite_inferior, 'tipo_anomalia'] = 'abaixo_normal'
        
        anomalias = df[df['anomalia'] == True]
        
        resultado = {
            'periodo_analisado': janela_dias,
            'media_vendas': float(media),
            'desvio_padrao': float(desvio),
            'limite_superior': float(limite_superior),
            'limite_inferior': float(limite_inferior),
            'total_anomalias': len(anomalias),
            'anomalias_detectadas': anomalias.to_dict('records'),
            'dados_completos': df.to_dict('records')
        }
        
        return resultado
    
    def salvar_modelos(self, diretorio='models'):
        """
        Salva os modelos treinados em disco
        """
        if not os.path.exists(diretorio):
            os.makedirs(diretorio)
        
        for nome, modelo in self.models.items():
            caminho_modelo = os.path.join(diretorio, f'{nome}_model.joblib')
            joblib.dump(modelo, caminho_modelo)
            
            if nome in self.scalers:
                caminho_scaler = os.path.join(diretorio, f'{nome}_scaler.joblib')
                joblib.dump(self.scalers[nome], caminho_scaler)
        
        print(f"Modelos salvos em: {diretorio}")
    
    def carregar_modelos(self, diretorio='models'):
        """
        Carrega modelos salvos do disco
        """
        for arquivo in os.listdir(diretorio):
            if arquivo.endswith('_model.joblib'):
                nome = arquivo.replace('_model.joblib', '')
                caminho_modelo = os.path.join(diretorio, arquivo)
                self.models[nome] = joblib.load(caminho_modelo)
                
                # Carregar scaler correspondente se existir
                caminho_scaler = os.path.join(diretorio, f'{nome}_scaler.joblib')
                if os.path.exists(caminho_scaler):
                    self.scalers[nome] = joblib.load(caminho_scaler)
        
        print(f"Modelos carregados de: {diretorio}")
    
    def close(self):
        """
        Fecha a conexão com o banco de dados
        """
        if self.session:
            self.session.close()

# Exemplo de uso
if __name__ == "__main__":
    ml_integration = RDSMLIntegration()
    
    if ml_integration.connect():
        print("Conectado ao banco de dados!")
        
        # Treinar modelo de previsão de vendas
        print("\n=== Treinando Modelo de Previsão de Vendas ===")
        resultado_treino = ml_integration.treinar_modelo_previsao_vendas()
        if resultado_treino:
            print(f"RMSE do modelo: {resultado_treino['rmse']:.2f}")
            
            # Fazer previsões
            print("\n=== Previsões para os Próximos 7 Dias ===")
            previsoes = ml_integration.prever_vendas_futuras(7)
            if previsoes:
                for prev in previsoes:
                    print(f"{prev['data']} ({prev['dia_semana']}): R$ {prev['vendas_previstas']:.2f}")
        
        # Segmentação RFM
        print("\n=== Segmentação RFM de Clientes ===")
        segmentacao = ml_integration.segmentar_clientes_rfm()
        if segmentacao:
            print(f"Total de clientes: {segmentacao['total_clientes']}")
            print("Distribuição por segmento:")
            for segmento, count in segmentacao['distribuicao_segmentos'].items():
                print(f"  {segmento}: {count} clientes")
        
        # Detecção de anomalias
        print("\n=== Detecção de Anomalias ===")
        anomalias = ml_integration.detectar_anomalias_vendas(30)
        if anomalias:
            print(f"Anomalias detectadas: {anomalias['total_anomalias']}")
            print(f"Média de vendas: R$ {anomalias['media_vendas']:.2f}")
        
        ml_integration.close()
    else:
        print("Falha ao conectar com o banco de dados!")

