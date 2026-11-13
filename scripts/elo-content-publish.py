#!/usr/bin/env python3
"""
ELO Content Publisher - Ferramenta direta para preparar e publicar conteúdo no Totem.
Garante integridade criptográfica do bundle, geração de variantes e atualização imediata do Totem.
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path

CONTENT_ROOT = Path('/var/home/jpereiratrindade/.local/share/elo/content')
DIST_STATE = Path('/var/home/jpereiratrindade/.local/share/elo-distribution/state')
SELECTION_FILE = DIST_STATE / 'selection.json'


def compute_content_hash(root: Path) -> str:
    files = {}
    for folder in ('catalog', 'assets'):
        directory = root / folder
        if not directory.exists():
            continue
        for parent, dirs, names in os.walk(directory):
            for name in dirs + names:
                path = Path(parent) / name
                if path.is_file() and not path.is_symlink():
                    files[path.relative_to(root).as_posix()] = path.read_bytes()

    digest = hashlib.sha256()
    for name, data in sorted(files.items()):
        digest.update(name.encode('utf-8'))
        digest.update(data)
    return 'sha256:' + digest.hexdigest()


def sync_bundle():
    """Garante que todos os átomos tenham variantes e atualiza o bundle ativo."""
    atoms_dir = CONTENT_ROOT / 'catalog/atoms'
    variants_file = CONTENT_ROOT / 'catalog/variants/variants.json'

    if not atoms_dir.exists():
        print(f"Diretório de átomos não encontrado: {atoms_dir}")
        return

    variants = json.loads(variants_file.read_text()) if variants_file.exists() else []
    known_content_ids = {v.get('content_id') for v in variants if v.get('role') == 'ambient'}

    added = 0
    all_atom_ids = []
    for f in sorted(atoms_dir.glob('*.json')):
        atom = json.loads(f.read_text())
        cid = atom.get('content_id')
        if not cid:
            continue
        all_atom_ids.append(cid)
        if cid not in known_content_ids:
            title = atom.get('title', cid)
            facts = atom.get('canonical_facts', [])
            text = facts[0].get('statement') if facts else atom.get('summary', title)
            images = atom.get('modalities', {}).get('image', [])
            variants.append({
                'variant_id': f'var_{cid}_ambient',
                'content_id': cid,
                'role': 'ambient',
                'audience': 'general',
                'interaction': 'none',
                'duration_hint_seconds': 10,
                'presentation': {
                    'title': title,
                    'text': text,
                    'media': images
                }
            })
            known_content_ids.add(cid)
            added += 1

    variants_file.parent.mkdir(parents=True, exist_ok=True)
    variants_file.write_text(json.dumps(variants, indent=2, ensure_ascii=False))

    # Atualiza o bundle ativo referenciado por 'current'
    current_link = CONTENT_ROOT / 'current'
    if current_link.exists():
        active_bundle = current_link.resolve()
        bundle_variants = active_bundle / 'catalog/variants/variants.json'
        bundle_variants.parent.mkdir(parents=True, exist_ok=True)
        bundle_variants.write_text(json.dumps(variants, indent=2, ensure_ascii=False))

        # Copia átomos atualizados para o bundle
        bundle_atoms = active_bundle / 'catalog/atoms'
        bundle_atoms.mkdir(parents=True, exist_ok=True)
        for f in atoms_dir.glob('*.json'):
            shutil.copy2(f, bundle_atoms / f.name)

        # Copia assets
        assets_src = CONTENT_ROOT / 'assets'
        assets_dst = active_bundle / 'assets'
        if assets_src.exists():
            shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)

        # Atualiza manifesto do bundle
        bundle_mf = active_bundle / 'manifest.json'
        if bundle_mf.exists():
            manifest = json.loads(bundle_mf.read_text())
            manifest['atom_ids'] = all_atom_ids
            bundle_mf.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

        # Recalcula hash criptográfico
        new_hash = compute_content_hash(active_bundle)
        manifest = json.loads(bundle_mf.read_text())
        manifest['content_hash'] = new_hash
        bundle_mf.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        print(f"Bundle ativo atualizado: {active_bundle.name} (Hash: {new_hash[:16]}...)")

    return variants


def apply_to_totem(exposure_seconds=10, selected_variant_ids=None):
    """Aplica as páginas selecionadas no totem imediatamente."""
    variants = sync_bundle()
    if not variants:
        print("Nenhuma variante encontrada.")
        return

    ambient_variants = [v['variant_id'] for v in variants if v.get('role') == 'ambient']
    target_variants = selected_variant_ids if selected_variant_ids else ambient_variants

    payload = {
        'exposure_seconds': exposure_seconds,
        'variants': target_variants
    }
    SELECTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    SELECTION_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\n[OK] Totem configurado com {len(target_variants)} página(s) ({exposure_seconds}s por tela):")
    for vid in target_variants:
        v = next((item for item in variants if item['variant_id'] == vid), None)
        title = v['presentation']['title'] if v else vid
        print(f"  • {title} ({vid})")


def list_content():
    sync_bundle()
    variants_file = CONTENT_ROOT / 'catalog/variants/variants.json'
    variants = json.loads(variants_file.read_text()) if variants_file.exists() else []

    current_selection = []
    if SELECTION_FILE.exists():
        try:
            current_selection = json.loads(SELECTION_FILE.read_text()).get('variants', [])
        except Exception:
            pass

    print(f"\n=== Catálogo de Conteúdo ELO ({len(variants)} variantes cadastradas) ===")
    for v in variants:
        active = "[ATIVO NO TOTEM]" if v['variant_id'] in current_selection else "                 "
        title = v['presentation'].get('title', '')
        media = v['presentation'].get('media', [])
        media_str = f" | Mídia: {media[0]}" if media else ""
        print(f"{active} {v['variant_id']:25} | {title}{media_str}")


def add_card(content_id, title, text, image_path=None):
    atoms_dir = CONTENT_ROOT / 'catalog/atoms'
    assets_images = CONTENT_ROOT / 'assets/images'
    assets_images.mkdir(parents=True, exist_ok=True)

    image_ref = []
    if image_path:
        src = Path(image_path)
        if not src.is_file():
            print(f"Erro: arquivo de imagem não encontrado: {image_path}")
            sys.exit(1)
        dest = assets_images / src.name
        shutil.copy2(src, dest)
        image_ref = [f'assets/images/{src.name}']
        print(f"Imagem copiada para: {dest}")

    atom_data = {
        'content_id': content_id,
        'title': title,
        'language': 'pt-BR',
        'type': 'entity',
        'modalities': {
            'image': image_ref,
            'audio': []
        },
        'canonical_facts': [
            {
                'fact_id': f'fact_{content_id}_1',
                'statement': text
            }
        ]
    }

    atom_file = atoms_dir / f'{content_id}.json'
    atom_file.parent.mkdir(parents=True, exist_ok=True)
    atom_file.write_text(json.dumps(atom_data, indent=2, ensure_ascii=False))
    print(f"Átomo criado: {atom_file}")

    apply_to_totem()


def main():
    parser = argparse.ArgumentParser(description="Publicador direto de conteúdo para o Totem ELO")
    parser.add_argument('--list', action='store_true', help="Listar conteúdo e status no Totem")
    parser.add_argument('--sync', action='store_true', help="Sincronizar todos os átomos e aplicar no Totem")
    parser.add_argument('--add', action='store_true', help="Adicionar novo cartão de conteúdo")
    parser.add_argument('--id', help="Identificador único (ex: species_tucano_001)")
    parser.add_argument('--title', help="Título da tela")
    parser.add_argument('--text', help="Texto explicativo ou fato principal")
    parser.add_argument('--image', help="Caminho do arquivo de imagem (JPG/PNG)")
    parser.add_argument('--seconds', type=int, default=10, help="Segundos por tela no Totem (padrão 10s)")

    args = parser.parse_args()

    if args.add:
        if not (args.id and args.title and args.text):
            print("Erro: --add requer --id, --title e --text")
            sys.exit(1)
        add_card(args.id, args.title, args.text, args.image)
    elif args.sync:
        apply_to_totem(exposure_seconds=args.seconds)
    elif args.list:
        list_content()
    else:
        list_content()


if __name__ == '__main__':
    main()
