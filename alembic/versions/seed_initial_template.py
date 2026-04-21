# ruff: noqa: E501, W291
# pyright: reportUnusedCallResult=false
"""Seed initial template

Revision ID: seed_initial_template
Revises: b92f05a72cb1
Create Date: 2026-04-21 20:03:00.000000+03:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "seed_initial_template"
down_revision: str | Sequence[str] | None = "b92f05a72cb1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Insert the consultation note template
    op.execute(
        """
        INSERT INTO medical_document_templates (id, name, description, version, is_active, created_at, updated_at)
        VALUES (
            '550e8400-e29b-41d4-a716-446655440010',
            'Протокол консультации',
            'Шаблон для оформления протокола консультации: ФИО пациента, дата визита, жалобы, анамнез, осмотр, диагноз, план лечения.',
            '1.0',
            true,
            NOW(),
            NOW()
        );
        """
    )

    # Insert template fields
    op.execute(
        """
        INSERT INTO template_fields (id, template_id, name, label, field_type, is_required, default_value, options, "order", created_at, updated_at)
        VALUES 
            ('550e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440010', 'patient_name', 'ФИО пациента', 'TEXT', true, NULL, NULL, 1, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440012', '550e8400-e29b-41d4-a716-446655440010', 'birth_date', 'Дата рождения', 'DATE', true, NULL, NULL, 2, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440013', '550e8400-e29b-41d4-a716-446655440010', 'gender', 'Пол', 'SELECT', true, NULL, '{"options": ["Мужской", "Женский"]}', 3, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440014', '550e8400-e29b-41d4-a716-446655440010', 'visit_date', 'Дата визита', 'DATE', true, NULL, NULL, 4, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440015', '550e8400-e29b-41d4-a716-446655440010', 'chief_complaint', 'Основная жалоба', 'TEXTAREA', true, NULL, NULL, 5, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440016', '550e8400-e29b-41d4-a716-446655440010', 'medical_history', 'Анамнез заболевания', 'TEXTAREA', false, NULL, NULL, 6, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440017', '550e8400-e29b-41d4-a716-446655440010', 'allergies', 'Аллергии', 'TEXTAREA', false, NULL, NULL, 7, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440018', '550e8400-e29b-41d4-a716-446655440010', 'examination', 'Данные осмотра', 'TEXTAREA', true, NULL, NULL, 8, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440019', '550e8400-e29b-41d4-a716-446655440010', 'diagnosis', 'Диагноз', 'TEXTAREA', true, NULL, NULL, 9, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440020', '550e8400-e29b-41d4-a716-446655440010', 'treatment_plan', 'План лечения', 'TEXTAREA', true, NULL, NULL, 10, NOW(), NOW()),
            ('550e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440010', 'doctor_name', 'ФИО врача','TEXT' , true , NULL , NULL ,  2, NOW(), NOW());
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Delete template fields
    op.execute(
        """
        DELETE FROM template_fields 
        WHERE template_id = '550e8400-e29b-41d4-a716-446655440010'
        """
    )

    # Delete the template
    op.execute(
        """
        DELETE FROM medical_document_templates 
        WHERE id = '550e8400-e29b-41d4-a716-446655440010'
        """
    )
