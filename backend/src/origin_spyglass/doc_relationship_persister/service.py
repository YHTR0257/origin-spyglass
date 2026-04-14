"""Doc Relationship Persister サービス実装"""

import uuid
from datetime import date as date_type
from pathlib import Path

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from origin_spyglass.infra.vector_store import DocumentRecord, uuid7

from .types import (
    DocRelationshipPersisterInput,
    DocRelationshipPersisterOutput,
    DuplicateDocumentError,
    MetadataValidationError,
)


def _build_display_id(source_file: str) -> str:
    """ソースファイル名から UI 表示向け識別子を生成する。

    例: "path/to/report.md" → "DOC-report"
    """
    return f"DOC-{Path(source_file).stem}"


def _validate_metadata(input: DocRelationshipPersisterInput) -> None:
    """メタデータの整合性を検証する。

    検証項目:
    - author が空でないこと（Pydantic では非 None のみ保証されるため）
    - source_file が空でないこと
    - domain が空でないこと

    Note:
        title は FrontmatterMeta.ensure_title() により常に非空が保証されるため、
        ここでの検証は不要。

    Raises:
        MetadataValidationError: いずれかのフィールドが不正な場合
    """
    meta = input.document.meta
    if not input.author.strip():
        raise MetadataValidationError(field="author", reason="author must not be empty")
    if not meta.source_file.strip():
        raise MetadataValidationError(field="source_file", reason="source_file must not be empty")
    if not meta.domain.strip():
        raise MetadataValidationError(field="domain", reason="domain must not be empty")


def _to_output(record: DocumentRecord) -> DocRelationshipPersisterOutput:
    return DocRelationshipPersisterOutput(
        doc_id=str(record.id),
        display_id=record.display_id,
        title=record.title,
        source_file=record.source_file,
        domain=record.domain,
        tags=record.tags,
        author=record.author,
        source_type=record.source_type,  # type: ignore[arg-type]
        confidence=record.confidence,
        date=record.date,
        created_at=record.created_at.isoformat(),
    )


class DocRelationshipPersisterService:
    """ドキュメントメタデータと本文を PostgreSQL に永続化するサービス

    persist() の処理フロー:
      1. メタデータバリデーション
      2. 重複チェック（title + 年 が一致するレコードの存在確認）
      3. UUIDv7 を割り当て
      4. INSERT して保存

    Args:
        session: SQLAlchemy AsyncSession
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist(self, input: DocRelationshipPersisterInput) -> DocRelationshipPersisterOutput:
        """ドキュメントを永続化する

        Args:
            input: 永続化するドキュメントの入力スキーマ

        Returns:
            永続化されたドキュメントの出力スキーマ

        Raises:
            MetadataValidationError: メタデータが不正な場合
            DuplicateDocumentError: 同一 title + 年のドキュメントが既に存在する場合
        """
        # 1. メタデータバリデーション
        _validate_metadata(input)

        meta = input.document.meta
        title = (meta.title or "").strip()

        # 2. 重複チェック（title + 年）
        year_start = date_type(input.date.year, 1, 1)
        year_end = date_type(input.date.year, 12, 31)
        dup_stmt = select(DocumentRecord).where(
            DocumentRecord.title == title,
            DocumentRecord.date >= year_start,
            DocumentRecord.date <= year_end,
        )
        dup_result = await self._session.execute(dup_stmt)
        existing = dup_result.scalar_one_or_none()
        if existing is not None:
            raise DuplicateDocumentError(
                doc_id=str(existing.id),
                title=title,
                year=input.date.year,
            )

        # 3. UUIDv7 を割り当て
        new_id = uuid7()
        display_id = _build_display_id(meta.source_file)

        # 4. INSERT して保存
        stmt = (
            insert(DocumentRecord)
            .values(
                id=new_id,
                display_id=display_id,
                title=title,
                source_file=meta.source_file,
                mime=input.document.mime,
                body=input.document.markdown,
                domain=meta.domain,
                tags=meta.tags,
                author=input.author,
                source_type=input.source_type.value,
                confidence=input.confidence,
                date=input.date,
            )
            .returning(DocumentRecord)
        )

        result = await self._session.execute(stmt)
        await self._session.commit()
        record = result.scalar_one()
        return _to_output(record)

    async def list_documents(
        self,
        domain: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DocRelationshipPersisterOutput]:
        """ドキュメント一覧を取得する

        Args:
            domain: フィルタするドメイン。None の場合は全件取得
            limit: 最大取得件数
            offset: オフセット

        Returns:
            ドキュメント出力スキーマのリスト
        """
        stmt = select(DocumentRecord)
        if domain is not None:
            stmt = stmt.where(DocumentRecord.domain == domain)
        stmt = stmt.order_by(DocumentRecord.created_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        return [_to_output(r) for r in result.scalars().all()]

    async def get_document(self, doc_id: str) -> DocRelationshipPersisterOutput | None:
        """doc_id（UUIDv7 文字列）でドキュメントを取得する

        Args:
            doc_id: ドキュメント識別子（UUIDv7 文字列）

        Returns:
            ドキュメント出力スキーマ、存在しない場合は None
        """
        try:
            uid = uuid.UUID(doc_id)
        except ValueError:
            return None

        stmt = select(DocumentRecord).where(DocumentRecord.id == uid)
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        return _to_output(record) if record is not None else None
