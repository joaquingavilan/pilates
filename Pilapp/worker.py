
import os
import sys
import json
import asyncio
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async def process_query(query):
    try:
        # Inicializar MCP Server
        mcp_server = MCPServerStdio(
            params={
                "command": "python",
                "args": ["mcp_bridge_server.py"],
                "timeout": 15,
                "kwargs": {"encoding": "latin1", "errors": "replace"}
            }
        )
        
        await mcp_server.connect()
        
        # Crear agente
        agent = Agent(
            name="TuPilates Assistant",
            instructions='''
            Eres un asistente virtual para clases de pilates. Tu tarea principal es ayudar a registrar
            alumnos y verificar disponibilidad de turnos.
            
            Para registrar un alumno regular, necesitas recopilar TODOS estos datos antes de usar 
            la herramienta registrar_alumno(). Para registrar un alumno ocasional, necesitas 
            recopilar TODOS estos datos antes de usar la herramienta registrar_alumno_ocasional().
            
            Cuando consultes por disponibilidad de turnos, debes informar exactamente lo que indique 
            el sistema sobre los lugares disponibles.
            ''',
            mcp_servers=[mcp_server],
        )
        
        # Procesar consulta
        result = await Runner.run(agent, query)
        return {"status": "success", "response": result.final_output}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Obtener la consulta desde argumentos
    query = sys.argv[1]
    
    # Ejecutar asyncio
    result = asyncio.run(process_query(query))
    
    # Imprimir resultado como JSON para que el proceso principal lo lea
    print(json.dumps(result))
