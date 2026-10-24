CREATE TABLE "books" (
  "id" UUID NOT NULL,
  "isbn" VARCHAR(13) NOT NULL,
  "title" VARCHAR(100) NOT NULL,
  "author" VARCHAR(80) NOT NULL,
  "version" INTEGER NOT NULL DEFAULT 1,
  CONSTRAINT "books_pkey" PRIMARY KEY ("id"),
  CONSTRAINT "books_version_positive" CHECK ("version" >= 1)
);

CREATE UNIQUE INDEX "uq_books_isbn" ON "books"("isbn");
