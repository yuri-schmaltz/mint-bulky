# Scripts de Migração para o Bulky

Scripts auxiliares para facilitar a migração de outras ferramentas para o Bulky, especialmente para casos que envolvem metadados (EXIF, ID3) ou processamento avançado.

## Scripts Disponíveis

### 1. `rename_exif.py`
Renomeia fotos usando metadados EXIF (data/hora original).

**Uso**:
```bash
python3 rename_exif.py /caminho/fotos [--apply]
```

### 2. `rename_by_hash.py`
Renomeia arquivos usando hash SHA256 (útil para deduplicação).

**Uso**:
```bash
python3 rename_by_hash.py /caminho/arquivos [--apply]
```

### 3. `normalize_names.sh`
Remove acentos, espaços extras e caracteres especiais.

**Uso**:
```bash
./normalize_names.sh arquivo1.txt arquivo2.pdf [--apply]
```

### 4. `extract_id3.sh`
Extrai metadados ID3 de arquivos MP3 e gera lista de renomeação.

**Uso**:
```bash
./extract_id3.sh /caminho/mp3s [--apply]
```

## Modo Dry-Run

Por padrão, todos os scripts rodam em modo **dry-run** (apenas mostram o que fariam).

Para aplicar as mudanças, adicione `--apply` ou edite o script e descomente a linha de `mv`/`rename`.

## Dependências

### Python
```bash
pip install Pillow  # Para rename_exif.py
```

### Shell
```bash
# Para extract_id3.sh (escolha um):
sudo apt install id3v2        # Ubuntu/Debian
sudo apt install ffmpeg       # Alternativa universal
```

## Workflow Recomendado

1. **Execute o script em dry-run** (sem --apply)
2. **Revise a saída** e confirme que os nomes estão corretos
3. **Faça backup** dos arquivos originais
4. **Execute com --apply** ou descomente as linhas de renomeação
5. **Use o Bulky** para ajustes finais (contadores, caixa, etc.)

## Exemplos

### Renomear fotos por data EXIF
```bash
# Dry-run
python3 migration_scripts/rename_exif.py ~/Fotos/Ferias2024

# Aplicar
python3 migration_scripts/rename_exif.py ~/Fotos/Ferias2024 --apply
```

### Normalizar nomes de documentos
```bash
# Dry-run
./migration_scripts/normalize_names.sh ~/Documentos/*.pdf

# Aplicar
./migration_scripts/normalize_names.sh ~/Documentos/*.pdf --apply
```

### Dedplicar por hash
```bash
python3 migration_scripts/rename_by_hash.py ~/Downloads --apply
# Depois use 'fdupes' ou 'rmlint' para remover duplicatas
```

## Suporte

Para bugs ou sugestões, abra uma issue no repositório do Bulky.
