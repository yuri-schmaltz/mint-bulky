#!/usr/bin/env python3
"""
rename_exif.py - Renomeia fotos usando metadados EXIF

Extrai DateTimeOriginal de fotos JPEG e renomeia no formato:
  YYYYMMDD_HHMMSS_NNN.jpg

Uso:
  python3 rename_exif.py /caminho/fotos           # Dry-run (apenas mostra)
  python3 rename_exif.py /caminho/fotos --apply   # Aplica as mudanças

Requer: pip install Pillow
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    print("❌ Erro: Pillow não está instalado")
    print("   Instale com: pip install Pillow")
    sys.exit(1)


def get_exif_date(image_path):
    """Extrai DateTimeOriginal do EXIF."""
    try:
        img = Image.open(image_path)
        exif = img._getexif()
        
        if exif:
            for tag, value in exif.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == 'DateTimeOriginal':
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        print(f"⚠️  Aviso ao ler EXIF de {image_path.name}: {e}", file=sys.stderr)
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Renomeia fotos usando data EXIF DateTimeOriginal'
    )
    parser.add_argument('directory', help='Diretório com as fotos')
    parser.add_argument('--apply', action='store_true', 
                       help='Aplicar mudanças (padrão: dry-run)')
    parser.add_argument('--prefix', default='', 
                       help='Prefixo opcional (ex: "ferias_")')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    
    if not directory.exists() or not directory.is_dir():
        print(f"❌ Erro: '{directory}' não é um diretório válido")
        sys.exit(1)
    
    # Coletar arquivos JPEG
    image_files = []
    for pattern in ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']:
        image_files.extend(directory.glob(pattern))
    
    if not image_files:
        print(f"❌ Nenhuma foto JPEG encontrada em {directory}")
        sys.exit(1)
    
    print(f"📷 Encontradas {len(image_files)} fotos em {directory}")
    print()
    
    # Processar cada imagem
    counter = 1
    successful = 0
    failed = 0
    
    for img_file in sorted(image_files):
        exif_date = get_exif_date(img_file)
        
        if exif_date:
            new_name = f"{args.prefix}{exif_date.strftime('%Y%m%d_%H%M%S')}_{counter:03d}{img_file.suffix.lower()}"
            status = "✅"
        else:
            # Fallback: usar contador sem data
            new_name = f"{args.prefix}IMG_{counter:04d}{img_file.suffix.lower()}"
            status = "⚠️ "
            failed += 1
        
        new_path = img_file.parent / new_name
        
        # Evitar sobrescrever arquivos existentes
        if new_path.exists() and new_path != img_file:
            print(f"❌ {img_file.name} → {new_name} (arquivo já existe!)")
            failed += 1
            counter += 1
            continue
        
        print(f"{status} {img_file.name:40s} → {new_name}")
        
        if args.apply:
            try:
                img_file.rename(new_path)
                successful += 1
            except Exception as e:
                print(f"   ❌ Erro ao renomear: {e}")
                failed += 1
        
        counter += 1
    
    print()
    print("─" * 60)
    
    if args.apply:
        print(f"✅ Renomeados com sucesso: {successful}")
        if failed > 0:
            print(f"❌ Falharam: {failed}")
    else:
        print("ℹ️  Modo DRY-RUN (nenhuma mudança aplicada)")
        print(f"   Para aplicar, execute: {sys.argv[0]} {args.directory} --apply")
    
    print("─" * 60)


if __name__ == '__main__':
    main()
