"""Document repository for database access."""
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.schemas.document import DocumentFilterParams


class DocumentRepository:
    """Handles database persistence, queries, and row-level locks for documents."""

    async def create(self, session: AsyncSession, document: Document) -> Document:
        """Persist a new document entity."""
        session.add(document)
        await session.flush()
        return document

    async def get_by_id(
        self, session: AsyncSession, doc_id: uuid.UUID
    ) -> Optional[Document]:
        """Fetch document by primary key."""
        stmt = (
            select(Document)
            .where(Document.id == doc_id)
            .options(
                selectinload(Document.client),
                selectinload(Document.property),
                selectinload(Document.uploader),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, doc_id: uuid.UUID
    ) -> Optional[Document]:
        """Fetch document with row-level locking (SELECT FOR UPDATE)."""
        stmt = (
            select(Document)
            .where(Document.id == doc_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_duplicate(
        self,
        session: AsyncSession,
        checksum: str,
        property_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
    ) -> Optional[Document]:
        """Check for active document with identical checksum under the same property or client."""
        stmt = select(Document).where(
            Document.checksum == checksum,
            Document.is_archived.is_(False),
        )

        if property_id is not None:
            stmt = stmt.where(Document.property_id == property_id)
        elif client_id is not None:
            stmt = stmt.where(Document.client_id == client_id)
        else:
            stmt = stmt.where(
                Document.property_id.is_(None),
                Document.client_id.is_(None),
            )

        result = await session.execute(stmt)
        return result.scalars().first()

    async def list_documents(
        self,
        session: AsyncSession,
        filters: DocumentFilterParams,
    ) -> Tuple[List[Document], int]:
        """Query documents with parameterized filtering and database-level pagination."""
        stmt = (
            select(Document)
            .options(
                selectinload(Document.client),
                selectinload(Document.property),
            )
        )
        count_stmt = select(func.count(Document.id))

        conditions = []

        if filters.property_id is not None:
            conditions.append(Document.property_id == filters.property_id)

        if filters.client_id is not None:
            conditions.append(Document.client_id == filters.client_id)

        if filters.document_type:
            conditions.append(
                Document.document_type == filters.document_type.strip().upper()
            )

        if filters.status:
            conditions.append(
                Document.status == filters.status.strip().upper()
            )

        if filters.is_archived is not None:
            conditions.append(Document.is_archived == filters.is_archived)

        if filters.search:
            s = filters.search.strip()
            conditions.append(
                or_(
                    Document.original_filename.ilike(f"%{s}%"),
                    Document.notes.ilike(f"%{s}%"),
                )
            )

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        count_res = await session.execute(count_stmt)
        total_count = count_res.scalar() or 0

        # Sorting
        sort_field = getattr(Document, filters.sort_by, Document.created_at)
        if filters.sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_field.asc(), Document.id.asc())
        else:
            stmt = stmt.order_by(sort_field.desc(), Document.id.desc())

        # Pagination
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await session.execute(stmt)
        documents = list(result.scalars().all())
        return documents, total_count

    async def update(
        self, session: AsyncSession, doc: Document, update_dict: dict
    ) -> Document:
        """Apply partial updates to document entity."""
        for key, value in update_dict.items():
            setattr(doc, key, value)
        await session.flush()
        return doc
