"""initial

Revision ID: eb707e76b7fd
Revises:
Create Date: 2026-08-25

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'eb707e76b7fd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Таблицы для закладок, лайков и рецензий.

    Каждая команда — отдельный op.execute(): asyncpg через SQLAlchemy
    использует extended query protocol и не может выполнить несколько
    команд в одном execute() (в отличие от простого asyncpg.execute()).
    """
    # Таблица закладок
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bookmarks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            movie_id UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_bookmark_user_movie UNIQUE (user_id, movie_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_user_id ON bookmarks(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_movie_id ON bookmarks(movie_id)")

    # Таблица лайков
    # rating: оценка от 0 до 10 (0 - дизлайк, 10 - лайк, 1-9 - промежуточные оценки)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS likes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            movie_id UUID NOT NULL,
            rating SMALLINT NOT NULL CHECK (rating >= 0 AND rating <= 10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_like_user_movie UNIQUE (user_id, movie_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_likes_user_id ON likes(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_likes_movie_id ON likes(movie_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_likes_movie_rating ON likes(movie_id, rating)")

    # Таблица рецензий
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            movie_id UUID NOT NULL,
            text TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 10),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_review_user_movie UNIQUE (user_id, movie_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reviews_movie_id ON reviews(movie_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reviews_movie_rating ON reviews(movie_id, rating)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating DESC)")

    # Таблица для голосования за рецензии (лайк/дизлайк)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS review_likes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            review_id UUID NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            is_like BOOLEAN NOT NULL, -- true = лайк, false = дизлайк
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_review_like_user_review UNIQUE (user_id, review_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_likes_user_id ON review_likes(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_likes_review_id ON review_likes(review_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_review_likes_review_is_like "
        "ON review_likes(review_id, is_like)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS review_likes")
    op.execute("DROP TABLE IF EXISTS reviews")
    op.execute("DROP TABLE IF EXISTS likes")
    op.execute("DROP TABLE IF EXISTS bookmarks")
