"""
Utilitários de IA para auxiliar em tarefas de banco de dados
"""

import re
import json
from datetime import datetime
import openai
import os

class DatabaseAIAssistant:
    """
    Assistente de IA para tarefas relacionadas a banco de dados
    """
    
    def __init__(self):
        # Configurar OpenAI (as variáveis de ambiente já estão configuradas)
        self.client = openai.OpenAI()
        
    def gerar_sql_from_natural_language(self, descricao, schema_info=None):
        """
        Gera consulta SQL a partir de descrição em linguagem natural
        """
        schema_context = ""
        if schema_info:
            schema_context = f"""
Contexto do esquema do banco de dados:
{schema_info}
"""
        
        prompt = f"""
Você é um especialista em SQL. Gere uma consulta SQL baseada na seguinte descrição:

{descricao}

{schema_context}

Regras:
1. Use apenas comandos SELECT seguros
2. Inclua comentários explicativos
3. Use boas práticas de SQL
4. Se a descrição for ambígua, faça suposições razoáveis
5. Retorne apenas o código SQL, sem explicações adicionais

SQL:
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um especialista em SQL que gera consultas precisas e seguras."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            sql_gerado = response.choices[0].message.content.strip()
            
            # Limpar e validar o SQL gerado
            sql_limpo = self._limpar_sql(sql_gerado)
            
            return {
                'sql': sql_limpo,
                'descricao_original': descricao,
                'valido': self._validar_sql_basico(sql_limpo),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'erro': str(e),
                'descricao_original': descricao,
                'timestamp': datetime.now().isoformat()
            }
    
    def otimizar_consulta_sql(self, sql_query):
        """
        Sugere otimizações para uma consulta SQL
        """
        prompt = f"""
Analise a seguinte consulta SQL e sugira otimizações:

```sql
{sql_query}
```

Forneça sugestões de otimização considerando:
1. Uso de índices
2. Reescrita de consultas
3. Eliminação de subconsultas desnecessárias
4. Uso de JOINs mais eficientes
5. Limitação de resultados quando apropriado

Formato da resposta:
- Consulta otimizada (se aplicável)
- Lista de sugestões específicas
- Explicação das melhorias
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um especialista em otimização de banco de dados."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2
            )
            
            otimizacao = response.choices[0].message.content.strip()
            
            return {
                'sql_original': sql_query,
                'sugestoes_otimizacao': otimizacao,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'erro': str(e),
                'sql_original': sql_query,
                'timestamp': datetime.now().isoformat()
            }
    
    def gerar_schema_from_description(self, descricao_sistema):
        """
        Gera esquema de banco de dados a partir da descrição de um sistema
        """
        prompt = f"""
Baseado na seguinte descrição de sistema, crie um esquema de banco de dados relacional:

{descricao_sistema}

Gere:
1. Tabelas com colunas apropriadas
2. Tipos de dados adequados
3. Chaves primárias e estrangeiras
4. Índices recomendados
5. Relacionamentos entre tabelas

Formate como SQL DDL (CREATE TABLE statements) com comentários explicativos.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um arquiteto de banco de dados especialista em modelagem relacional."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1200,
                temperature=0.3
            )
            
            schema_sql = response.choices[0].message.content.strip()
            
            return {
                'descricao_sistema': descricao_sistema,
                'schema_sql': schema_sql,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'erro': str(e),
                'descricao_sistema': descricao_sistema,
                'timestamp': datetime.now().isoformat()
            }
    
    def explicar_plano_execucao(self, plano_execucao):
        """
        Explica um plano de execução de consulta SQL em linguagem simples
        """
        prompt = f"""
Explique o seguinte plano de execução de consulta SQL em linguagem simples e clara:

{plano_execucao}

Inclua:
1. O que cada etapa faz
2. Possíveis gargalos
3. Sugestões de melhoria
4. Estimativa de performance (se possível identificar)

Use linguagem acessível para desenvolvedores que não são especialistas em banco de dados.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um tutor de banco de dados que explica conceitos complexos de forma simples."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.4
            )
            
            explicacao = response.choices[0].message.content.strip()
            
            return {
                'plano_original': plano_execucao,
                'explicacao': explicacao,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'erro': str(e),
                'plano_original': plano_execucao,
                'timestamp': datetime.now().isoformat()
            }
    
    def gerar_dados_teste(self, schema_table, num_registros=10):
        """
        Gera dados de teste realistas para uma tabela
        """
        prompt = f"""
Gere {num_registros} registros de dados de teste realistas para a seguinte estrutura de tabela:

{schema_table}

Requisitos:
1. Dados devem ser realistas e consistentes
2. Respeitar tipos de dados e restrições
3. Gerar como comandos INSERT SQL
4. Usar dados em português brasileiro quando aplicável
5. Incluir variedade nos dados

Formate como comandos INSERT prontos para execução.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um gerador de dados de teste que cria informações realistas e consistentes."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            dados_sql = response.choices[0].message.content.strip()
            
            return {
                'schema_original': schema_table,
                'num_registros': num_registros,
                'dados_sql': dados_sql,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'erro': str(e),
                'schema_original': schema_table,
                'timestamp': datetime.now().isoformat()
            }
    
    def detectar_problemas_schema(self, schema_sql):
        """
        Analisa um esquema SQL e detecta possíveis problemas
        """
        prompt = f"""
Analise o seguinte esquema de banco de dados e identifique possíveis problemas:

{schema_sql}

Verifique:
1. Problemas de normalização
2. Falta de índices importantes
3. Tipos de dados inadequados
4. Relacionamentos mal definidos
5. Questões de performance
6. Problemas de segurança
7. Convenções de nomenclatura

Para cada problema encontrado, forneça:
- Descrição do problema
- Impacto potencial
- Sugestão de correção
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um auditor de banco de dados especialista em identificar problemas de design."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            analise = response.choices[0].message.content.strip()
            
            return {
                'schema_original': schema_sql,
                'analise_problemas': analise,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'erro': str(e),
                'schema_original': schema_sql,
                'timestamp': datetime.now().isoformat()
            }
    
    def _limpar_sql(self, sql):
        """
        Limpa e formata o SQL gerado
        """
        # Remover blocos de código markdown se existirem
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)
        
        # Remover espaços extras
        sql = sql.strip()
        
        return sql
    
    def _validar_sql_basico(self, sql):
        """
        Validação básica de segurança do SQL
        """
        sql_upper = sql.upper()
        
        # Comandos perigosos
        comandos_perigosos = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 
            'ALTER', 'CREATE', 'GRANT', 'REVOKE'
        ]
        
        for comando in comandos_perigosos:
            if comando in sql_upper:
                return False
        
        # Deve começar com SELECT
        if not sql_upper.strip().startswith('SELECT'):
            return False
        
        return True
    
    def gerar_documentacao_tabela(self, nome_tabela, schema_table):
        """
        Gera documentação automática para uma tabela
        """
        prompt = f"""
Gere documentação técnica completa para a seguinte tabela de banco de dados:

Nome da tabela: {nome_tabela}
Esquema:
{schema_table}

A documentação deve incluir:
1. Propósito da tabela
2. Descrição de cada coluna
3. Relacionamentos com outras tabelas
4. Índices e sua finalidade
5. Regras de negócio implícitas
6. Exemplos de uso comum
7. Considerações de performance

Formate em Markdown para fácil leitura.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um documentador técnico especialista em banco de dados."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            documentacao = response.choices[0].message.content.strip()
            
            return {
                'nome_tabela': nome_tabela,
                'schema_original': schema_table,
                'documentacao_markdown': documentacao,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'erro': str(e),
                'nome_tabela': nome_tabela,
                'timestamp': datetime.now().isoformat()
            }

# Exemplo de uso
if __name__ == "__main__":
    ai_assistant = DatabaseAIAssistant()
    
    # Exemplo 1: Gerar SQL a partir de linguagem natural
    print("=== Geração de SQL ===")
    resultado_sql = ai_assistant.gerar_sql_from_natural_language(
        "Mostre os 10 clientes que mais gastaram no último mês",
        schema_info="Tabelas: clientes (id_cliente, nome, email), pedidos (id_pedido, id_cliente, data_pedido, valor_total)"
    )
    
    if 'sql' in resultado_sql:
        print(f"SQL gerado:\n{resultado_sql['sql']}")
    else:
        print(f"Erro: {resultado_sql.get('erro', 'Erro desconhecido')}")
    
    # Exemplo 2: Gerar esquema
    print("\n=== Geração de Esquema ===")
    resultado_schema = ai_assistant.gerar_schema_from_description(
        "Sistema de biblioteca com livros, autores, usuários e empréstimos"
    )
    
    if 'schema_sql' in resultado_schema:
        print(f"Schema gerado:\n{resultado_schema['schema_sql'][:200]}...")
    else:
        print(f"Erro: {resultado_schema.get('erro', 'Erro desconhecido')}")
    
    # Exemplo 3: Gerar dados de teste
    print("\n=== Geração de Dados de Teste ===")
    resultado_dados = ai_assistant.gerar_dados_teste(
        "CREATE TABLE produtos (id INT PRIMARY KEY, nome VARCHAR(255), preco DECIMAL(10,2), categoria VARCHAR(100));",
        num_registros=5
    )
    
    if 'dados_sql' in resultado_dados:
        print(f"Dados de teste:\n{resultado_dados['dados_sql'][:200]}...")
    else:
        print(f"Erro: {resultado_dados.get('erro', 'Erro desconhecido')}")

