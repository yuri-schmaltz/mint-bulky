#!/usr/bin/env python3
"""
rename_by_hash.py - Renomeia arquivos usando hash SHA256

Útil para deduplicação e organização de arquivos baixados.
Formato: <hash16>.<ext>

Uso:
  python3 rename_by_hash.py /caminho/arquivos           # Dry-run
  python3 rename_by_hash.py /caminho/arquivos --apply   # Aplica
"""
import sys
import argparse
import hashlib
from pathlib import Path


def hash_file(filepath, algorithm='sha256', length=16):
    """Calcula hash do arquivo."""
    h = hashlib.new(algorithm)
    
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()[:length]
    except Exception as e:
        print(f"⚠️  Erro ao calcular hash de {filepath.name}: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Renomeia arquivos usando hash SHA256'
    )
    parser.add_argument('directory', help='Diretório com os arquivos')
    parser.add_argument('--apply', action='store_true',
                       help='Aplicar mudanças (padrão: dry-run)')
    parser.add_argument('--length', type=int, default=16,
                       help='Tamanho do hash em caracteres (padrão: 16)')
    parser.add_argument('--algorithm', default='sha256',
                       choices=['md5', 'sha1', 'sha256'],
                       help='Algoritmo de hash (padrão: sha256)')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    
    if not directory.exists() or not directory.is_dir():
        print(f"❌ Erro: '{directory}' não é um diretório válido")
        sys.exit(1)
    
    # Coletar arquivos
    files = [f for f in directory.iterdir() if f.is_file()]
    
    if not files:
        print(f"❌ Nenhum arquivo encontrado em {directory}")
        sys.exit(1)
    
    print(f"📁 Encontrados {len(files)} arquivos em {directory}")
    print(f"🔐 Algoritmo: {args.algorithm.upper()}, comprimento: {args.length}")
    print()
    
    successful = 0
    failed = 0
    duplicates = {}
    
    for file_path in sorted(files):
        file_hash = hash_file(file_path, args.algorithm, args.length)
        
        if file_hash is None:
            failed += 1
            continue
        
        new_name = f"{file_hash}{file_path.suffix}"
        new_path = file_path.parent / new_name
        
        # Detectar duplicatas
        if file_hash in duplicates:
            print(f"🔄 {file_path.name:40s} → {new_name} (DUPLICATA de {duplicates[file_hash]})")
            failed += 1
            continue
        
        duplicates[file_hash] = file_path.name
        
        # Evitar sobrescrever
        if new_path.exists() and new_path != file_path:
            print(f"❌ {file_path.name:40s} → {new_name} (arquivo já existe!)")
            failed += 1
            continue
        
        print(f"✅ {file_path.name:40s} → {new_name}")
        
        if args.apply:
            try:
                file_path.rename(new_path)
                successful += 1
            except Exception as e:
                print(f"   ❌ Erro ao renomear: {e}")
                failed += 1
    
    print()
    print("─" * 60)
    
    if args.apply:
        print(f"✅ Renomeados com sucesso: {successful}")
        if failed > 0:
            print(f"❌ Falharam ou duplicados: {failed}")
    else:
        print("ℹ️  Modo DRY-RUN (nenhuma mudança aplicada)")
        print(f"   Para aplicar, execute: {sys.argv[0]} {args.directory} --apply")
    
    print("─" * 60)


if __name__ == '__main__':
    main()
