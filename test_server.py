#!/usr/bin/env python3
"""
Script de teste para verificar se o servidor está recebendo dados dos sensores
"""
import subprocess
import time
import os
import json

def monitor_logs():
    """Monitora o diretório de logs e mostra quando novos JSONs são criados"""
    logs_dir = os.path.join(os.path.dirname(__file__), "server", "logs")
    
    print(f"Monitorando diretório: {logs_dir}")
    print("=" * 60)
    
    # Aguarda a pasta ser criada
    for _ in range(10):
        if os.path.exists(logs_dir):
            break
        print("Aguardando servidor iniciar...")
        time.sleep(1)
    
    existing_files = set()
    
    print("\n[AGUARDANDO DADOS DOS SENSORES...]")
    print("Pressione Ctrl+C para interromper\n")
    
    while True:
        try:
            if os.path.exists(logs_dir):
                files = set(os.listdir(logs_dir))
                new_files = files - existing_files
                
                for filename in new_files:
                    filepath = os.path.join(logs_dir, filename)
                    print(f"\n✓ NOVO ARQUIVO CRIADO: {filename}")
                    
                    # Tenta ler o arquivo
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            print(f"  Último registro: {data[-1] if data else 'vazio'}")
                    except:
                        pass
                
                # Conta registros em cada arquivo
                for filename in files:
                    filepath = os.path.join(logs_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                            print(f"  {filename}: {len(data)} registros")
                    except:
                        pass
                
                existing_files = files
            
            time.sleep(2)
        except KeyboardInterrupt:
            print("\n\nMonitoramento interrompido.")
            break

if __name__ == "__main__":
    monitor_logs()
