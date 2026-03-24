"""
Script para aplicar reemplazos Barra → Retira en app.py de Dylan Restaurant.
Uso: python apply_replacements.py <ruta_al_app.py_original>
Genera: app_retira.py en el mismo directorio
"""
import sys

def apply_replacements(content):
    replacements = [
        ('"mostrador": "BARRA"', '"mostrador": "RETIRA"'),
        ('"barra": "BARRA"', '"barra": "RETIRA"'),
        ('"mostrador": "🧍 Barra"', '"mostrador": "🧍 Retira"'),
        ('"barra": "🧍 Barra"', '"barra": "🧍 Retira"'),
        ('"🧍 BARRA"', '"🧍 RETIRA"'),
        ('"🍺 BARRA"', '"🍺 RETIRA"'),
        ('🔴 BARRA —', '🔴 RETIRA —'),
        ('f"Barra #{count + 1}"', 'f"Retira #{count + 1}"'),
        ('order_table_num = "Barra"', 'order_table_num = "Retira"'),
        ('"Barra" in occupied_map', '"Retira" in occupied_map'),
        ("occupied_map['Barra']", "occupied_map['Retira']"),
        ('"🧍 Barra"', '"🧍 Retira"'),
        ('🧾 Barra / Delivery', '🧾 Retira / Delivery'),
        ('Barra / Delivery sin cobrar', 'Retira / Delivery sin cobrar'),
        ('# Barra — also check if occupied', '# Retira — also check if occupied'),
        ('# Auto-number barra orders', '# Auto-number retira orders'),
        ('# Mesa/barra — combined print', '# Mesa/retira — combined print'),
        ('# Mozo en mesa/barra', '# Mozo en mesa/retira'),
        ('# ── Barra / Delivery pending', '# ── Retira / Delivery pending'),
        ('# Separate mesa orders vs barra/delivery', '# Separate mesa orders vs retira/delivery'),
        ('barra_occupied', 'retira_occupied'),
        ('tab_barra', 'tab_retira'),
    ]

    for old, new in replacements:
        content = content.replace(old, new)

    return content

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python apply_replacements.py <ruta_app.py>")
        sys.exit(1)

    input_path = sys.argv[1]
    with open(input_path, 'r', encoding='utf-8') as f:
        original = f.read()

    modified = apply_replacements(original)

    output_path = input_path.replace('.py', '_retira.py')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(modified)

    # Verificar
    import re
    remaining = [(i+1, line.strip()[:100]) for i, line in enumerate(modified.split('\n')) if re.search(r'barra', line, re.IGNORECASE)]

    print(f"✅ Archivo guardado: {output_path}")
    print(f"📊 Ocurrencias 'barra' restantes: {len(remaining)} (deberían ser 7)")
    for ln, text in remaining:
        print(f"   L{ln}: {text}")
