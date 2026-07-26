# msgfmt.py - Minimal PO to MO compiler in pure Python
import sys
import os
import struct

def compile_po(po_path, mo_path):
    """Compila un archivo .po a un archivo binario .mo."""
    if not os.path.exists(po_path):
        print(f"Error: {po_path} no existe.")
        return False
        
    messages = {}
    with open(po_path, 'r', encoding='utf-8') as f:
        msgid = None
        msgstr = None
        in_msgid = False
        in_msgstr = False
        
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('msgid'):
                in_msgid = True
                in_msgstr = False
                # Quitar 'msgid ' y las comillas
                msgid = line[5:].strip().strip('"')
            elif line.startswith('msgstr'):
                in_msgid = False
                in_msgstr = True
                msgstr = line[6:].strip().strip('"')
            elif line.startswith('"') and line.endswith('"'):
                val = line.strip('"')
                if in_msgid:
                    msgid += val
                elif in_msgstr:
                    msgstr += val
                    
            if msgid is not None and msgstr is not None and not in_msgid and not in_msgstr:
                # Reemplazar escapes habituales
                msgid_clean = msgid.replace('\\n', '\n').replace('\\t', '\t')
                msgstr_clean = msgstr.replace('\\n', '\n').replace('\\t', '\t')
                messages[msgid_clean] = msgstr_clean
                msgid = None
                msgstr = None

    # Escribir formato MO
    keys = sorted(messages.keys())
    offsets = []
    ids = []
    strs = []
    
    for key in keys:
        val = messages[key]
        ids.append(key.encode('utf-8'))
        strs.append(val.encode('utf-8'))

    # Cabecera MO format
    # Magic: 0x950412de
    magic = 0x950412de
    version = 0
    num_strings = len(keys)
    
    # Offsets iniciales
    key_offset = 28
    val_offset = key_offset + num_strings * 8
    
    header = struct.pack('<Iiiiiii', magic, version, num_strings, key_offset, val_offset, 0, 0)
    
    # Calcular offsets de claves y valores
    key_table = []
    val_table = []
    
    current_key_pos = val_offset + num_strings * 8
    for id_bytes in ids:
        length = len(id_bytes)
        key_table.append(struct.pack('<ii', length, current_key_pos))
        current_key_pos += length + 1 # +1 para el terminador nulo

    current_val_pos = current_key_pos
    for str_bytes in strs:
        length = len(str_bytes)
        val_table.append(struct.pack('<ii', length, current_val_pos))
        current_val_pos += length + 1

    # Escribir archivo final
    with open(mo_path, 'wb') as f:
        f.write(header)
        for kt in key_table:
            f.write(kt)
        for vt in val_table:
            f.write(vt)
        for id_bytes in ids:
            f.write(id_bytes + b'\x00')
        for str_bytes in strs:
            f.write(str_bytes + b'\x00')
            
    print(f"Compilado con éxito: {po_path} -> {mo_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python msgfmt.py archivo.po archivo.mo")
        sys.exit(1)
    compile_po(sys.argv[1], sys.argv[2])
