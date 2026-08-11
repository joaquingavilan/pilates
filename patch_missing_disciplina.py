import sys

def patch_missing_disciplina(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Fix registrar_asistencias
    target_1 = '        asistieron = data.get("asistieron", [])'
    replacement_1 = '        asistieron = data.get("asistieron", [])\n        disciplina = data.get("disciplina", "Reformer")'
    if target_1 in content:
        content = content.replace(target_1, replacement_1)
        print("Patched registrar_asistencias")
    else:
        print("Could not find target_1")

    # 2. Fix verificar_clase_hoy
    target_2 = '            horario = data.get("horario")  # Ejemplo: "19:00"'
    replacement_2 = '            horario = data.get("horario")  # Ejemplo: "19:00"\n            disciplina = data.get("disciplina", "Reformer")'
    if target_2 in content:
        content = content.replace(target_2, replacement_2)
        print("Patched verificar_clase_hoy")
    else:
        print("Could not find target_2")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    patch_missing_disciplina("C:/Users/jesus/Documents/pilates/Pilapp/views.py")
