def obter_horarios_disponiveis(horarios_ocupados):
    # Passo 1: O Universo Total
    todos_os_horarios = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]

    # Passo 2: A Restrição Fixa (Almoço)
    todos_os_horarios.remove("12:00")

    # Passo 3: Preparar a resposta
    horarios_livres = []

    # Passo 4: A Lógica de Filtragem
    for horario in todos_os_horarios:
        if horario not in horarios_ocupados:
            horarios_livres.append(horario)
            
    # Devolve o resultado
    return horarios_livres

# --- ÁREA DE TESTES ---
agenda_do_dia = ["09:00", "14:00", "15:00"]
resultado = obter_horarios_disponiveis(agenda_do_dia)

print("Os horários que sobraram livres são:")
print(resultado)