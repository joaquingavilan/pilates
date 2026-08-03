import re

with open('Pilapp/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the block for Turno.objects.get(dia=dia_turno, horario=data["hora_turno"])
pattern = r'turno = Turno\.objects\.get\(dia=dia_turno, horario=data\["hora_turno"\]\)\s+except Turno\.DoesNotExist:\s+errores\.append\(f"El turno \{dia_turno\} \{data\[\'hora_turno\'\]\} no existe\."\)'
new_block = """disciplina = data.get("disciplina", "Reformer")
            turno = Turno.objects.get(dia=dia_turno, horario=data["hora_turno"], disciplina=disciplina)
        except Turno.DoesNotExist:
            errores.append(f"El turno {dia_turno} {data['hora_turno']} ({disciplina}) no existe.")"""

content = re.sub(pattern, new_block, content)

with open('Pilapp/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched Pilapp/views.py successfully.")
