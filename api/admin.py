from django.contrib import admin
from .models import (
    Template, Proposal, ProposalCategory, ProposalVariable,
    ProposalElement, ProposalVariableValue, ProposalElementValue, Contract
)

class ProposalCategoryInline(admin.TabularInline):
    model = ProposalCategory
    extra = 1
    
class ProposalVariableInline(admin.TabularInline):
    model = ProposalVariable
    extra = 1

class ProposalElementInline(admin.TabularInline):
    model = ProposalElement
    extra = 1
    
class ProposalVariableValueInline(admin.TabularInline):
    model = ProposalVariableValue
    extra = 1

class ProposalElementValueInline(admin.TabularInline):
    model = ProposalElementValue
    extra = 1

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']
    inlines = [ProposalCategoryInline, ProposalVariableInline]

@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ['name', 'template', 'created_at', 'global_markup_percentage']
    list_filter = ['template', 'created_at']
    search_fields = ['name']
    inlines = [
        ProposalCategoryInline, 
        ProposalVariableInline, 
        ProposalElementInline,
        ProposalVariableValueInline,
        ProposalElementValueInline
    ]

@admin.register(ProposalCategory)
class ProposalCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'template', 'proposal', 'position']
    list_filter = ['template', 'proposal']
    search_fields = ['name']
    inlines = [ProposalElementInline]

@admin.register(ProposalVariable)
class ProposalVariableAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'default_value', 'template', 'proposal']
    list_filter = ['type', 'template', 'proposal']
    search_fields = ['name']

@admin.register(ProposalElement)
class ProposalElementAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'material_cost', 'labor_cost', 'markup_percentage', 'position']
    list_filter = ['category', 'proposal']
    search_fields = ['name']

@admin.register(ProposalVariableValue)
class ProposalVariableValueAdmin(admin.ModelAdmin):
    list_display = ['proposal', 'variable', 'value']
    list_filter = ['proposal', 'variable']
    search_fields = ['proposal__name', 'variable__name']

@admin.register(ProposalElementValue)
class ProposalElementValueAdmin(admin.ModelAdmin):
    list_display = ['proposal', 'element', 'calculated_material_cost', 'calculated_labor_cost', 'markup_percentage']
    list_filter = ['proposal', 'element']
    search_fields = ['proposal__name', 'element__name']

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['proposal', 'client_name', 'contractor_name', 'created_at', 'client_signed_at', 'contractor_signed_at']
    list_filter = ['created_at', 'client_signed_at', 'contractor_signed_at']
    search_fields = ['proposal__name', 'client_name', 'contractor_name']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Proposal Information', {
            'fields': ('proposal',)
        }),
        ('Client Information', {
            'fields': ('client_name', 'client_signature', 'client_initials', 'client_signed_at')
        }),
        ('Contractor Information', {
            'fields': ('contractor_name', 'contractor_signature', 'contractor_initials', 'contractor_signed_at')
        }),
        ('Contract Details', {
            'fields': ('terms_and_conditions', 'created_at')
        }),
    )