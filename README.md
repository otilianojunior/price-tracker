# Price Tracker

Sistema de monitoramento de preços e identificação de promoções do Mercado Livre, com persistência em PostgreSQL e publicação automática de ofertas no Telegram.

O projeto foi desenvolvido para coletar produtos e ofertas, acompanhar alterações de preço, identificar promoções elegíveis, gerar links de afiliado e publicar as melhores oportunidades em um canal/grupo do Telegram.

---

## Objetivo

O Price Tracker monitora categorias selecionadas do Mercado Livre e executa periodicamente um fluxo de:

1. autenticação no Mercado Livre;
2. descoberta de produtos;
3. coleta de ofertas e preços;
4. persistência dos dados no PostgreSQL;
5. identificação de quedas de preço;
6. aplicação das regras de elegibilidade;
7. geração de link de afiliado;
8. preparação da publicação;
9. envio da oferta para o Telegram;
10. registro da publicação no banco de dados.

O sistema foi estruturado para permitir a inclusão futura de outros canais de publicação.

---

## Arquitetura

```text
Mercado Livre
      │
      ▼
MercadoLivreCollector
      │
      ▼
MercadoLivreService
      │
      ├── Produtos
      ├── Ofertas
      ├── Preços
      └── Promoções
              │
              ▼
      ApplicationService
              │
              ▼
      Regras de publicação
              │
              ▼
      PublicationService
              │
              ├── AffiliateLinkService
              │
              ├── PublicationFormatter
              │
              └── NotificationService
                        │
                        ▼
                TelegramPublisher
                        │
                        ▼
              Telegram — Ofertas
```

O `Scheduler` controla a execução periódica da aplicação.

---

## Tecnologias

* Python
* SQLAlchemy
* PostgreSQL
* psycopg
* Docker
* Docker Compose
* Telegram Bot API
* Requests
* Mercado Livre API
* n8n — disponível no ambiente para futuras automações

---

## Estrutura do projeto

```text
price-tracker/
├── src/
│   ├── auth/
│   │   ├── exceptions.py
│   │   ├── mercado_livre.py
│   │   └── mercado_livre_browser.py
│   │
│   ├── collectors/
│   │   ├── mercado_livre.py
│   │   ├── mercado_livre_categories.py
│   │   ├── mercado_livre_client.py
│   │   └── mercado_livre_payment.py
│   │
│   ├── database/
│   │   ├── database.py
│   │   └── models.py
│   │
│   ├── notifications/
│   │   ├── service.py
│   │   ├── telegram.py
│   │   └── telegram_admin.py
│   │
│   ├── processors/
│   │
│   ├── scheduler/
│   │   └── scheduler.py
│   │
│   └── services/
│       ├── admin_notification_service.py
│       ├── affiliate_link_service.py
│       ├── application_service.py
│       ├── execution_service.py
│       ├── mercado_livre_affiliate.py
│       ├── mercado_livre_service.py
│       ├── publication_formatter.py
│       └── publication_service.py
│
├── scripts/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── requirements.txt
├── run.py
└── README.md
```

---

## Banco de dados

O sistema utiliza PostgreSQL como banco principal.

As entidades principais são:

* `plataformas`
* `categorias`
* `produtos`
* `ofertas`
* `precos`
* `promocoes`
* `links_afiliados`
* `canais_publicacao`
* `publicacoes`
* `autenticacoes_oauth`
* `rotacao_coleta`

### Produtos

Armazena os produtos monitorados e sua relação com plataforma e categoria.

### Ofertas

Representa as ofertas de um produto, incluindo vendedor, item externo, URL e condições de envio.

### Preços

Mantém o histórico de preços das ofertas.

### Promoções

Registra quedas de preço e descontos identificados pelo sistema.

### Publicações

Registra cada tentativa de publicação e seu resultado.

Os estados principais são:

```text
pendente
publicado
erro
```

Uma promoção possui seu próprio ciclo de estado:

```text
detectada
    │
    ▼
publicada
```

Em caso de falha na publicação, a promoção permanece `detectada` para permitir uma nova tentativa.

---

## Descoberta de produtos

A descoberta utiliza as categorias configuradas para o Mercado Livre.

Categorias atualmente utilizadas:

* celulares
* games
* informática
* TVs
* periféricos gamer
* armazenamento
* componentes de PC
* monitores

A descoberta utiliza uma rotação por categoria:

```text
1–10
  ↓
11–20
  ↓
1–10
  ↓
11–20
  ...
```

A rotação é persistida no banco de dados para que o próximo ciclo continue de onde o anterior terminou.

Por enquanto, a rotação está limitada aos blocos `1–10` e `11–20`.

---

## Monitoramento

Além da descoberta de novos produtos, o sistema monitora produtos já conhecidos.

A cada rodada, os produtos ativos mais antigos em relação à última verificação são priorizados para novo monitoramento.

Isso permite detectar quedas de preço mesmo quando o produto não está sendo descoberto novamente pela rotação.

---

## Regras de promoção

Na primeira coleta de uma oferta, uma promoção pode ser identificada quando existe um preço original maior que o preço atual.

Nas coletas seguintes, uma nova promoção é identificada quando:

```text
preço atual < preço anterior
```

São calculados:

* preço anterior;
* preço atual;
* preço original;
* desconto percentual;
* redução percentual.

Quando não existe queda de preço, nenhuma nova promoção é criada.

---

## Regras de publicação

O sistema evita republicações desnecessárias.

Para uma oferta já publicada:

### Dentro de 24 horas

A nova promoção só pode ser publicada se:

```text
novo preço < último preço publicado
```

Portanto:

```text
Preço igual     → não publica
Preço maior     → não publica
Preço menor     → pode publicar
```

### Após 24 horas

Uma nova promoção pode ser publicada novamente, desde que seja uma promoção elegível.

---

## Fluxo de publicação

Quando uma promoção é considerada elegível:

1. a promoção é carregada;
2. a oferta e o produto são validados;
3. a categoria é validada;
4. a configuração de afiliado é validada;
5. as informações de preço são preparadas;
6. o link de afiliado é obtido;
7. a publicação é criada com status `pendente`;
8. a mensagem é enviada ao Telegram;
9. o ID da mensagem externa é armazenado;
10. a publicação recebe status `publicado`;
11. a promoção recebe status `publicada`.

Se o envio falhar:

```text
Publicacao → erro
Promoção   → detectada
```

Isso permite que a promoção continue disponível para uma nova tentativa.

---

## Telegram

O projeto utiliza um bot do Telegram para publicar as ofertas.

A publicação utiliza:

```text
Telegram Bot API
      ↓
sendPhoto
      ↓
imagem do produto + legenda HTML
```

As configurações são mantidas no `.env`:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

O `TELEGRAM_CHAT_ID` corresponde ao grupo/supergrupo utilizado para acompanhar as ofertas.

### Teste de integração

A integração com o Telegram já foi validada utilizando diretamente a API e também através da classe:

```text
TelegramPublisher
```

O método utilizado pelo fluxo de publicação é:

```python
send_photo()
```

---

## Mercado Livre

A integração com o Mercado Livre utiliza autenticação OAuth e a sessão necessária para as operações suportadas pelo projeto.

A busca genérica:

```text
/sites/MLB/search
```

não é utilizada como mecanismo principal de descoberta devido às restrições encontradas durante a implementação.

A descoberta utiliza os endpoints de destaque/categoria e posteriormente consulta produtos e ofertas.

---

## Links de afiliado

O projeto possui uma camada específica para geração e gerenciamento dos links de afiliado:

```text
AffiliateLinkService
```

A configuração do programa de afiliados é mantida no banco de dados.

O identificador de afiliado não deve ser colocado diretamente no código-fonte.

---

## Scheduler

A execução principal é controlada pelo:

```text
PriceTrackerScheduler
```

O intervalo configurado atualmente é de:

```text
10 minutos
```

A aplicação pode ser executada uma única vez ou continuamente.

### Execução única

```bash
python run.py
```

### Execução contínua

O scheduler utiliza o intervalo definido na configuração do projeto.

---

## Docker

O ambiente local utiliza Docker Compose.

Serviços principais:

```text
n8n
PostgreSQL
```

O PostgreSQL utiliza:

```text
database: price_tracker
```

O n8n está disponível localmente para futuras automações e integrações.

---

## Configuração

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Depois preencha as configurações necessárias.

Entre elas:

```env
ML_CLIENT_ID=
ML_CLIENT_SECRET=
ML_REDIRECT_URI=

ML_AFFILIATE_TAG=
ML_MIN_DISCOUNT_PCT=

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

CHECK_INTERVAL_MINUTES=10
```

Nunca versione o `.env`.

Credenciais, cookies, sessões e outros dados sensíveis também não devem ser adicionados ao Git.

---

## Ambiente Python

É recomendado utilizar um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```
---

## Segurança

Nunca versionar:

* `.env`
* tokens de bots
* credenciais
* cookies
* sessões de navegador
* tokens OAuth
* arquivos de configuração sensíveis
* bancos de dados locais
* arquivos JSON contendo credenciais ou tokens

O projeto possui `.gitignore` configurado para evitar o versionamento desses arquivos.

---

## Licença

Projeto em desenvolvimento privado.
