"""Geração do time da máquina (CPU) usado nos campeonatos.

Sorteia jogadores do próprio catálogo, tentando várias combinações até achar
um time cujo overall médio fique perto do alvo (ex: 75).
"""

import random

import config
from players_data import jogadores_por_posicao


def gerar_time_maquina(modo: str, media_alvo: float = 75, tolerancia: float = 2, tentativas: int = 4000):
    """Retorna uma lista de jogadores (dicts do catálogo) formando um time válido
    pra o modo informado, com overall médio o mais próximo possível de media_alvo.
    """
    formacao = config.FORMACOES[modo]
    melhor_time, melhor_diff = None, None

    for _ in range(tentativas):
        time = []
        for posicao, quantidade in formacao.items():
            candidatos = jogadores_por_posicao(posicao)
            time.extend(random.sample(candidatos, quantidade))

        media = sum(j["overall"] for j in time) / len(time)
        diff = abs(media - media_alvo)

        if diff <= tolerancia:
            return time
        if melhor_diff is None or diff < melhor_diff:
            melhor_diff, melhor_time = diff, time

    return melhor_time  # não achou dentro da tolerância; devolve o mais próximo encontrado
