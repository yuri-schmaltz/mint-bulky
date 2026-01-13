# Exemplos de Uso dos Scripts de Migração

Este diretório contém arquivos de teste para demonstrar os scripts de migração.

## Arquivos de Teste

Os seguintes arquivos foram criados para demonstração:

```
arquivo  com   espaços.txt              # Espaços extras
DOCUMENTO [SITE] Nome_Estranho.doc      # Caracteres especiais, uppercase
Relatório com Acentuação.pdf            # Acentos
test_file_1.txt                         # Já normalizado
```

## Demonstrações

### 1. Normalização de Nomes

**Comando**:
```bash
../normalize_names.sh *
```

**Resultado (dry-run)**:
```
📝 Normalizando 4 arquivo(s)...

✅ arquivo  com   espaços.txt → arquivo_com_espacos.txt
✅ DOCUMENTO [SITE] Nome_Estranho.doc → documento_site_nome_estranho.doc
✅ Relatório com Acentuação.pdf → relatorio_com_acentuacao.pdf
✓  test_file_1.txt (já normalizado)

────────────────────────────────────────────────────────────
ℹ️  Modo DRY-RUN (nenhuma mudança aplicada)
   Para aplicar, adicione --apply ao comando
────────────────────────────────────────────────────────────
```

### 2. Renomeação por Hash

**Comando**:
```bash
python3 ../rename_by_hash.py .
```

**Resultado (dry-run)**:
```
📁 Encontrados 4 arquivos em .
🔐 Algoritmo: SHA256, comprimento: 16

✅ DOCUMENTO [SITE] Nome_Estranho.doc       → 5f3dc7b54baac0ab.doc
✅ Relatório com Acentuação.pdf             → 83a62aa049d5ee39.pdf
✅ arquivo  com   espaços.txt               → a1fff0ffefb9eace.txt
✅ test_file_1.txt                          → aa6afbd364592df9.txt

────────────────────────────────────────────────────────────
ℹ️  Modo DRY-RUN (nenhuma mudança aplicada)
   Para aplicar, execute: rename_by_hash.py . --apply
────────────────────────────────────────────────────────────
```

## Workflow Típico

### Cenário: Limpar Downloads Bagunçados

1. **Normalizar nomes primeiro**:
   ```bash
   cd ~/Downloads
   /path/to/normalize_names.sh * --apply
   ```

2. **Depois ajustar no Bulky**:
   - Adicionar contadores: `documento_%00n`
   - Alterar caso necessário
   - Organizar por data/categoria

### Cenário: Organizar Fotos

1. **Extrair metadados EXIF**:
   ```bash
   python3 /path/to/rename_exif.py ~/Fotos/Ferias --prefix "ferias2024_" --apply
   ```
   
   Resultado: `ferias2024_20240115_143522_001.jpg`

2. **Ajustar detalhes no Bulky**:
   - Remover prefixo se necessário
   - Adicionar local/evento
   - Normalizar extensões

### Cenário: Processar Biblioteca de Música

1. **Extrair metadados ID3**:
   ```bash
   /path/to/extract_id3.sh ~/Musica/Downloads --apply
   ```
   
   Resultado: `The_Beatles_-_Hey_Jude.mp3`

2. **Organizar no Bulky**:
   - Ajustar separadores
   - Normalizar caixa
   - Adicionar ano se disponível via script customizado

## Dicas

- **Sempre teste em dry-run primeiro!**
- **Faça backup antes de aplicar mudanças em massa**
- **Combine scripts**: normalize → hash/exif → bulky refinements
- **Use `git` no diretório de trabalho** para controlar versões:
  ```bash
  cd ~/Fotos
  git init
  git add .
  git commit -m "Backup antes de renomear"
  # ... aplicar scripts ...
  git diff --name-status  # Ver mudanças
  ```

## Criar Seus Próprios Scripts

Baseie-se nos scripts existentes e adapte para suas necessidades:

1. **Copie um script existente** como template
2. **Modifique a lógica de renomeação** (manter estrutura de dry-run/apply)
3. **Teste com arquivos de exemplo** neste diretório
4. **Documente** o caso de uso no README principal

## Restaurar Estado Original

Se aplicou mudanças e quer reverter:

```bash
# Se usou git
git checkout .

# Se não usou git, recrie os arquivos de teste
rm *
cat > test_file_1.txt << 'EOF'
Este é um arquivo de teste 1
EOF
# ... etc
```
