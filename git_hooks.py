"""
Utilitários para integração com Git e versionamento de esquema de banco de dados
"""

import os
import subprocess
import json
from datetime import datetime
import hashlib

class GitDatabaseVersioning:
    """
    Classe para gerenciar versionamento de esquema de banco de dados com Git
    """
    
    def __init__(self, repo_path='.'):
        self.repo_path = repo_path
        self.migrations_path = os.path.join(repo_path, 'src/database/migrations')
        
    def verificar_git_repo(self):
        """
        Verifica se o diretório é um repositório Git
        """
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def inicializar_git_repo(self):
        """
        Inicializa um repositório Git se não existir
        """
        if not self.verificar_git_repo():
            try:
                subprocess.run(['git', 'init'], cwd=self.repo_path, check=True)
                print("Repositório Git inicializado com sucesso!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Erro ao inicializar repositório Git: {e}")
                return False
        return True
    
    def criar_migration(self, nome, sql_content):
        """
        Cria um novo arquivo de migração
        """
        if not os.path.exists(self.migrations_path):
            os.makedirs(self.migrations_path)
        
        # Obter próximo número de versão
        versao = self._obter_proxima_versao()
        
        # Nome do arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"V{versao}__{nome}.sql"
        caminho_arquivo = os.path.join(self.migrations_path, nome_arquivo)
        
        # Conteúdo da migração
        header = f"""-- Migração V{versao}: {nome}
-- Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Autor: Sistema Automatizado
-- Hash: {hashlib.md5(sql_content.encode()).hexdigest()[:8]}

"""
        
        conteudo_completo = header + sql_content
        
        # Escrever arquivo
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo_completo)
        
        print(f"Migração criada: {nome_arquivo}")
        return caminho_arquivo
    
    def _obter_proxima_versao(self):
        """
        Obtém o próximo número de versão baseado nos arquivos existentes
        """
        if not os.path.exists(self.migrations_path):
            return 1
        
        arquivos = [f for f in os.listdir(self.migrations_path) if f.startswith('V') and f.endswith('.sql')]
        
        if not arquivos:
            return 1
        
        versoes = []
        for arquivo in arquivos:
            try:
                # Extrair número da versão (V1__, V2__, etc.)
                versao_str = arquivo.split('__')[0][1:]  # Remove 'V' e pega até '__'
                versoes.append(int(versao_str))
            except (ValueError, IndexError):
                continue
        
        return max(versoes) + 1 if versoes else 1
    
    def listar_migrations(self):
        """
        Lista todas as migrações disponíveis
        """
        if not os.path.exists(self.migrations_path):
            return []
        
        arquivos = [f for f in os.listdir(self.migrations_path) if f.endswith('.sql')]
        arquivos.sort()
        
        migrations = []
        for arquivo in arquivos:
            caminho_completo = os.path.join(self.migrations_path, arquivo)
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                linhas = f.readlines()
            
            # Extrair informações do header
            info = {
                'arquivo': arquivo,
                'caminho': caminho_completo,
                'versao': None,
                'nome': None,
                'data': None,
                'hash': None
            }
            
            for linha in linhas[:10]:  # Verificar apenas as primeiras linhas
                if linha.startswith('-- Migração V'):
                    parts = linha.split(':')
                    if len(parts) >= 2:
                        info['versao'] = parts[0].split('V')[1].strip()
                        info['nome'] = parts[1].strip()
                elif linha.startswith('-- Data:'):
                    info['data'] = linha.split(':', 1)[1].strip()
                elif linha.startswith('-- Hash:'):
                    info['hash'] = linha.split(':', 1)[1].strip()
            
            migrations.append(info)
        
        return migrations
    
    def commit_migration(self, arquivo_migration, mensagem=None):
        """
        Faz commit de uma migração no Git
        """
        if not self.verificar_git_repo():
            print("Não é um repositório Git. Inicializando...")
            if not self.inicializar_git_repo():
                return False
        
        try:
            # Adicionar arquivo ao staging
            subprocess.run(['git', 'add', arquivo_migration], cwd=self.repo_path, check=True)
            
            # Criar mensagem de commit se não fornecida
            if not mensagem:
                nome_arquivo = os.path.basename(arquivo_migration)
                mensagem = f"Add migration: {nome_arquivo}"
            
            # Fazer commit
            subprocess.run(['git', 'commit', '-m', mensagem], cwd=self.repo_path, check=True)
            
            print(f"Migração commitada com sucesso: {mensagem}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Erro ao fazer commit: {e}")
            return False
    
    def verificar_status_migrations(self):
        """
        Verifica o status das migrações no Git
        """
        try:
            # Verificar arquivos não commitados
            result = subprocess.run(
                ['git', 'status', '--porcelain', self.migrations_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            linhas = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            status = {
                'migrations_nao_commitadas': [],
                'migrations_modificadas': [],
                'migrations_novas': []
            }
            
            for linha in linhas:
                if linha:
                    estado = linha[:2]
                    arquivo = linha[3:]
                    
                    if estado == '??':
                        status['migrations_novas'].append(arquivo)
                    elif estado == ' M' or estado == 'M ':
                        status['migrations_modificadas'].append(arquivo)
                    else:
                        status['migrations_nao_commitadas'].append(arquivo)
            
            return status
            
        except subprocess.CalledProcessError as e:
            print(f"Erro ao verificar status: {e}")
            return None
    
    def criar_branch_para_migration(self, nome_feature):
        """
        Cria uma nova branch para desenvolvimento de uma feature que requer migração
        """
        try:
            nome_branch = f"feature/db-{nome_feature.lower().replace(' ', '-')}"
            
            # Criar e mudar para a nova branch
            subprocess.run(['git', 'checkout', '-b', nome_branch], cwd=self.repo_path, check=True)
            
            print(f"Branch criada e ativada: {nome_branch}")
            return nome_branch
            
        except subprocess.CalledProcessError as e:
            print(f"Erro ao criar branch: {e}")
            return None
    
    def gerar_relatorio_historico(self):
        """
        Gera um relatório do histórico de migrações
        """
        try:
            # Obter log do Git para arquivos de migração
            result = subprocess.run([
                'git', 'log', '--oneline', '--', self.migrations_path
            ], cwd=self.repo_path, capture_output=True, text=True, check=True)
            
            commits = []
            for linha in result.stdout.strip().split('\n'):
                if linha:
                    parts = linha.split(' ', 1)
                    if len(parts) == 2:
                        commits.append({
                            'hash': parts[0],
                            'mensagem': parts[1]
                        })
            
            # Obter informações detalhadas de cada commit
            historico = []
            for commit in commits[:10]:  # Últimos 10 commits
                try:
                    result_detail = subprocess.run([
                        'git', 'show', '--stat', '--format=%an|%ad|%s', commit['hash']
                    ], cwd=self.repo_path, capture_output=True, text=True, check=True)
                    
                    linhas = result_detail.stdout.split('\n')
                    if linhas:
                        info_linha = linhas[0].split('|')
                        if len(info_linha) >= 3:
                            historico.append({
                                'hash': commit['hash'],
                                'autor': info_linha[0],
                                'data': info_linha[1],
                                'mensagem': info_linha[2],
                                'arquivos_alterados': [l for l in linhas[1:] if '.sql' in l]
                            })
                except subprocess.CalledProcessError:
                    continue
            
            return historico
            
        except subprocess.CalledProcessError as e:
            print(f"Erro ao gerar relatório: {e}")
            return []
    
    def validar_migration_syntax(self, arquivo_migration):
        """
        Valida a sintaxe básica de uma migração
        """
        try:
            with open(arquivo_migration, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            # Verificações básicas
            erros = []
            
            # Verificar se tem header
            if not conteudo.startswith('-- Migração V'):
                erros.append("Migração deve começar com header padrão")
            
            # Verificar comandos SQL perigosos
            comandos_perigosos = ['DROP DATABASE', 'TRUNCATE', 'DELETE FROM']
            for comando in comandos_perigosos:
                if comando in conteudo.upper():
                    erros.append(f"Comando perigoso detectado: {comando}")
            
            # Verificar se termina com ponto e vírgula
            linhas_sql = [l.strip() for l in conteudo.split('\n') if l.strip() and not l.strip().startswith('--')]
            if linhas_sql and not linhas_sql[-1].endswith(';'):
                erros.append("Última instrução SQL deve terminar com ponto e vírgula")
            
            return {
                'valida': len(erros) == 0,
                'erros': erros,
                'arquivo': arquivo_migration
            }
            
        except Exception as e:
            return {
                'valida': False,
                'erros': [f"Erro ao ler arquivo: {str(e)}"],
                'arquivo': arquivo_migration
            }

# Exemplo de uso
if __name__ == "__main__":
    git_db = GitDatabaseVersioning()
    
    # Verificar se é um repo Git
    if not git_db.verificar_git_repo():
        print("Inicializando repositório Git...")
        git_db.inicializar_git_repo()
    
    # Criar uma migração de exemplo
    sql_exemplo = """
CREATE TABLE exemplo (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nome VARCHAR(255) NOT NULL,
    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_exemplo_nome ON exemplo(nome);
"""
    
    arquivo = git_db.criar_migration("create_exemplo_table", sql_exemplo)
    
    # Validar migração
    validacao = git_db.validar_migration_syntax(arquivo)
    if validacao['valida']:
        print("Migração válida!")
        
        # Fazer commit
        git_db.commit_migration(arquivo, "Adicionar tabela de exemplo")
    else:
        print("Erros na migração:")
        for erro in validacao['erros']:
            print(f"  - {erro}")
    
    # Listar migrações
    print("\nMigrações disponíveis:")
    for migration in git_db.listar_migrations():
        print(f"  {migration['arquivo']} - {migration['nome']}")
    
    # Verificar status
    status = git_db.verificar_status_migrations()
    if status:
        print(f"\nStatus: {len(status['migrations_novas'])} novas, {len(status['migrations_modificadas'])} modificadas")

