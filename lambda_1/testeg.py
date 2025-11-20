import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Adiciona o diretório pai ao path para que o Python encontre o pacote 'lambda_1'
# Isso é necessário para rodar o teste diretamente do PyCharm ou do terminal
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa a função que queremos testar
from lambda_1 import agente_geral


class TestAgenteGeral(unittest.TestCase):

    def setUp(self):
        """
        Garante que o modelo seja resetado antes de cada teste.
        Isso evita que o teste 5 contamine os outros.
        """
        agente_geral.flash_model = MagicMock()

    def criar_mock_resposta(self, texto):
        """Cria um objeto de resposta simulado com o atributo .text"""
        mock_resp = MagicMock()
        mock_resp.text = texto
        return mock_resp

    # ---------------------------------------------------------------------
    # Teste 1: O "caminho feliz" para uma pergunta SIMPLES
    # ---------------------------------------------------------------------
    @patch('lambda_1.agente_geral.flash_model')
    def test_caminho_simples(self, mock_flash_model):
        """
        Testa o fluxo de uma pergunta 'simples'.
        """
        pergunta = "O que é reflorestamento?"
        mock_resp_classificacao = self.criar_mock_resposta(
            json.dumps({"complexidade": "simples", "agente_destino": "geral"})
        )
        mock_resp_direta = self.criar_mock_resposta(
            "Reflorestamento é o processo de replantar árvores em uma área."
        )
        mock_flash_model.generate_content.side_effect = [
            mock_resp_classificacao,
            mock_resp_direta
        ]

        mensagem = {
            "payload": {"question": pergunta},
            "metadata": {"trace_id": "test-simple-123"}
        }
        resultado = agente_geral.executar(mensagem)

        self.assertEqual(resultado["original_question"], pergunta)
        self.assertEqual(resultado["classification"]["complexidade"], "simples")
        self.assertEqual(resultado["answer"], "Reflorestamento é o processo de replantar árvores em uma área.")
        self.assertEqual(mock_flash_model.generate_content.call_count, 2)

    # ---------------------------------------------------------------------
    # Teste 2: O "caminho feliz" para uma pergunta COMPLEXA
    # ---------------------------------------------------------------------
    @patch('lambda_1.agente_geral.flash_model')
    def test_caminho_complexo(self, mock_flash_model):
        """
        Testa o fluxo de uma pergunta 'complexa'.
        """
        pergunta = "Minha proposta é usar drones para monitorar."
        mock_resp_classificacao = self.criar_mock_resposta(
            json.dumps({"complexidade": "complexa", "agente_destino": "avaliador"})
        )
        mock_flash_model.generate_content.return_value = mock_resp_classificacao

        mensagem = {
            "payload": {"question": pergunta},
            "metadata": {"trace_id": "test-complex-456"}
        }
        resultado = agente_geral.executar(mensagem)

        self.assertEqual(resultado["classification"]["complexidade"], "complexa")
        self.assertEqual(resultado["next_agent"], "avaliador")
        self.assertEqual(resultado["answer"], "")
        self.assertEqual(mock_flash_model.generate_content.call_count, 1)

    # ---------------------------------------------------------------------
    # Teste 3: Teste de Falha (Resposta de classificação mal formatada)
    # ---------------------------------------------------------------------
    @patch('lambda_1.agente_geral.flash_model')
    def test_falha_json(self, mock_flash_model):
        """
        Testa o 'try/except' de fallback se a IA retornar um JSON inválido.
        """
        pergunta = "O que é... ?"
        mock_resp_classificacao = self.criar_mock_resposta("Ops, eu não sou um JSON.")
        mock_flash_model.generate_content.return_value = mock_resp_classificacao

        mensagem = {
            "payload": {"question": pergunta},
            "metadata": {"trace_id": "test-fallback-789"}
        }
        resultado = agente_geral.executar(mensagem)

        self.assertEqual(resultado["classification"]["complexidade"], "complexa")
        self.assertEqual(resultado["next_agent"], "geral")
        self.assertEqual(mock_flash_model.generate_content.call_count, 1)

    # ---------------------------------------------------------------------
    # Teste 4: Teste de Erro (Input inválido)
    # ---------------------------------------------------------------------
    def test_falha_sem_pergunta(self):
        """
        Testa se a função levanta um ValueError se 'question' não for fornecida.
        """
        mensagem = {"payload": {"not_a_question": "teste"}}
        with self.assertRaisesRegex(ValueError, "não contém uma 'question'"):
            agente_geral.executar(mensagem)

    # ---------------------------------------------------------------------
    # Teste 5: Teste de Erro (Modelo não inicializado)
    # ---------------------------------------------------------------------
    def test_falha_modelo_nao_inicializado(self):
        """
        Testa se a função levanta um RuntimeError se o modelo for None.
        """
        # Força o modelo a ser None para este teste específico
        agente_geral.flash_model = None

        mensagem = {"payload": {"question": "Olá"}}
        with self.assertRaisesRegex(RuntimeError, "Modelo Gemini Flash não está disponível"):
            agente_geral.executar(mensagem)


if __name__ == '__main__':
    unittest.main()
