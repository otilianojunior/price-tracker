from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Plataforma(Base):
    __tablename__ = "plataformas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    url_base: Mapped[str | None] = mapped_column(String(500))
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)

    nome: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
    )

    configuracao_afiliacao_id: Mapped[int | None] = mapped_column(
        ForeignKey("configuracoes_afiliacao.id"),
        nullable=True,
    )

    ativa: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class RotacaoColeta(Base):
    __tablename__ = "rotacoes_coleta"

    id: Mapped[int] = mapped_column(primary_key=True)

    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias.id"),
        unique=True,
        nullable=False,
    )

    proxima_posicao: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class Produto(Base):
    __tablename__ = "produtos"

    __table_args__ = (
        UniqueConstraint(
            "plataforma_id",
            "produto_id_externo",
            name="uq_produtos_plataforma_produto_externo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    plataforma_id: Mapped[int] = mapped_column(
        ForeignKey("plataformas.id"),
        nullable=False,
    )

    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias.id"),
        nullable=False,
    )

    produto_id_externo: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    nome: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    url_produto: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )

    imagem_principal: Mapped[str | None] = mapped_column(
        String(2000)
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    ultima_verificacao_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

class Oferta(Base):
    __tablename__ = "ofertas"

    __table_args__ = (
        UniqueConstraint(
            "produto_id",
            "item_id_externo",
            name="uq_ofertas_produto_item_externo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    produto_id: Mapped[int] = mapped_column(
        ForeignKey("produtos.id"),
        nullable=False,
    )

    item_id_externo: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    vendedor: Mapped[str | None] = mapped_column(
        String(200)
    )

    vendedor_id_externo: Mapped[str | None] = mapped_column(
        String(100)
    )

    loja_oficial_id: Mapped[str | None] = mapped_column(
        String(100)
    )

    url_oferta: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )

    frete_gratis: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    moeda: Mapped[str] = mapped_column(
        String(10),
        default="BRL",
        nullable=False,
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class Preco(Base):
    __tablename__ = "precos"

    id: Mapped[int] = mapped_column(primary_key=True)

    oferta_id: Mapped[int] = mapped_column(
        ForeignKey("ofertas.id"),
        nullable=False,
    )

    preco: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    preco_original: Mapped[float | None] = mapped_column(
        Numeric(12, 2)
    )

    desconto_percentual: Mapped[float | None] = mapped_column(
        Numeric(5, 2)
    )

    parcelas: Mapped[int | None] = mapped_column()

    valor_parcela: Mapped[float | None] = mapped_column(
        Numeric(12, 2)
    )

    sem_juros: Mapped[bool | None] = mapped_column()

    forma_pagamento: Mapped[str | None] = mapped_column()
 
    coletado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class Promocao(Base):
    __tablename__ = "promocoes"

    id: Mapped[int] = mapped_column(primary_key=True)

    oferta_id: Mapped[int] = mapped_column(
        ForeignKey("ofertas.id"),
        nullable=False,
    )

    preco_anterior: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    preco_atual: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    preco_original: Mapped[float | None] = mapped_column(
        Numeric(12, 2)
    )

    desconto_percentual: Mapped[float | None] = mapped_column(
        Numeric(5, 2)
    )

    reducao_percentual: Mapped[float | None] = mapped_column(
        Numeric(5, 2)
    )

    texto_sugestao: Mapped[str | None] = mapped_column(
        String(5000)
    )

    detectada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="detectada",
    )

class LinkAfiliado(Base):
    __tablename__ = "links_afiliados"

    id: Mapped[int] = mapped_column(primary_key=True)

    promocao_id: Mapped[int] = mapped_column(
        ForeignKey("promocoes.id"),
        nullable=False,
    )

    oferta_id: Mapped[int] = mapped_column(
        ForeignKey("ofertas.id"),
        nullable=False,
    )

    url_original: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )

    url_afiliado: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )

    tag: Mapped[str | None] = mapped_column(
        String(100)
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

class CanalPublicacao(Base):
    __tablename__ = "canais_publicacao"

    id: Mapped[int] = mapped_column(primary_key=True)

    nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    codigo: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    ativo: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class Publicacao(Base):
    __tablename__ = "publicacoes"

    id: Mapped[int] = mapped_column(primary_key=True)

    promocao_id: Mapped[int] = mapped_column(
        ForeignKey("promocoes.id"),
        nullable=False,
    )

    oferta_id: Mapped[int] = mapped_column(
        ForeignKey("ofertas.id"),
        nullable=False,
    )

    link_afiliado_id: Mapped[int] = mapped_column(
        ForeignKey("links_afiliados.id"),
        nullable=False,
    )

    canal_id: Mapped[int] = mapped_column(
        ForeignKey("canais_publicacao.id"),
        nullable=False,
    )

    texto_publicado: Mapped[str | None] = mapped_column(
        String(5000)
    )

    preco_publicado: Mapped[float | None] = mapped_column(
        Numeric(12, 2)
    )

    desconto_publicado: Mapped[float | None] = mapped_column(
        Numeric(5, 2)
    )

    mensagem_externa_id: Mapped[str | None] = mapped_column(
        String(200)
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pendente",
    )

    publicado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    erro: Mapped[str | None] = mapped_column(
        String(5000)
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class AutenticacaoOAuth(Base):
    __tablename__ = "autenticacoes_oauth"

    __table_args__ = (
        UniqueConstraint(
            "plataforma_id",
            name="uq_autenticacoes_oauth_plataforma",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    plataforma_id: Mapped[int] = mapped_column(
        ForeignKey("plataformas.id"),
        nullable=False,
    )

    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    refresh_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    tipo_token: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Bearer",
    )

    expira_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    escopos: Mapped[str | None] = mapped_column(
        Text
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class ConfiguracaoAfiliacao(Base):
    __tablename__ = "configuracoes_afiliacao"

    id: Mapped[int] = mapped_column(primary_key=True)

    nome: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    codigo: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    tag_afiliado: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    canal_id: Mapped[int] = mapped_column(
        ForeignKey("canais_publicacao.id"),
        nullable=False,
    )

    ativa: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )