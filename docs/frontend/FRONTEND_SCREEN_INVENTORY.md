# FRONTEND SCREEN INVENTORY

## Overview
This document contains the complete inventory of screens required for the RED_V1 frontend, derived directly from the Phase 18 API contracts and backend entities.

## Authentication
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Login** | Authenticate users and acquire JWTs | Public | `/login` | `login` (POST `/api/v1/auth/login`) | P0 |

## Dashboard
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Overview** | High-level summary of tasks, visits, alerts | CONSULTANT | `/dashboard` | View metrics, jump to tasks | P1 |

## Properties
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Property List (Private)** | Manage all properties | CONSULTANT | `/properties` | Search, filter, sort, paginate, create new | P0 |
| **Property Details (Private)** | View/edit full property data, view images | CONSULTANT | `/properties/:id` | Edit, publish, archive, pause, mark-sold | P0 |
| **Property Form (Create/Edit)** | Enter property details | CONSULTANT | `/properties/new` | Save, cancel, manage images | P0 |
| **Property Intelligence** | View TN verification details | CONSULTANT | `/properties/:id/verification` | Run verification, view evidence | P1 |

## Clients & Leads
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Client List** | Directory of clients | CONSULTANT | `/clients` | Filter, search, create new | P0 |
| **Client Details** | View client info and associated leads | CONSULTANT | `/clients/:id` | Edit, view related leads, archive | P0 |
| **Client Form (Create/Edit)** | Enter client information | CONSULTANT | `/clients/new` | Save, cancel | P0 |
| **Lead List** | Track sales leads | CONSULTANT | `/leads` | Filter by status, search | P0 |
| **Lead Details** | View lead lifecycle and actions | CONSULTANT | `/leads/:id` | Transition state (Contacted, Site Visit, etc.) | P0 |
| **Lead Form (Create/Edit)** | Create a new lead | CONSULTANT | `/leads/new` | Save, cancel | P0 |

## Requirements & Matching
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Requirements List** | View property requirements | CONSULTANT | `/requirements` | Filter, create | P1 |
| **Requirement Details** | View req details, trigger matching | CONSULTANT | `/requirements/:id` | Edit, Fulfill, Cancel, Find Matches | P1 |
| **Requirement Form** | Create property requirement | CONSULTANT | `/requirements/new` | Save, cancel | P1 |
| **Matches View** | Display candidate properties for a req | CONSULTANT | `/requirements/:id/matches`| View match score, navigate to property | P1 |

## Documents
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Document List** | Manage secure documents | CONSULTANT | `/documents` | Upload, search, preview, archive | P1 |
| **Document Details** | View metadata and download | CONSULTANT | `/documents/:id` | Edit metadata, download binary, review | P1 |
| **Upload Document (Modal/Page)** | Upload new files | CONSULTANT | `/documents/upload` | Select file, progress, save | P1 |

## Site Visits
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Site Visits List** | Manage schedule | CONSULTANT | `/site-visits` | Filter by status/date | P0 |
| **Site Visit Details** | View visit info, property, client | CONSULTANT | `/site-visits/:id` | Confirm, Complete, Reschedule, Cancel | P0 |
| **Site Visit Form** | Schedule a visit | CONSULTANT | `/site-visits/new` | Select property/client, pick time | P0 |

## Follow-ups
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Follow-ups List** | Manage task list | CONSULTANT | `/follow-ups` | Filter by completion/date | P1 |
| **Follow-up Details** | View task context | CONSULTANT | `/follow-ups/:id` | Mark complete, mark missed | P1 |
| **Follow-up Form** | Create a task | CONSULTANT | `/follow-ups/new` | Save, cancel | P1 |

## System & Activity
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Notifications Center** | View alerts | CONSULTANT | `/notifications` | Read/unread toggle, link to resource | P1 |
| **Audit Logs** | Immutable system actions | CONSULTANT | `/audit-logs` | Filter, search, paginate | P2 |

## Public/External
| Screen | Purpose | Role | Route | Key Actions | Priority |
|--------|---------|------|-------|-------------|----------|
| **Public Property Directory** | View published properties | Public | `/public/properties` | Search, filter | P2 |
| **Public Property Details** | View property details, request visit | Public | `/public/properties/:ref` | Request Site Visit | P2 |
| **Public Visit Status** | Check requested visit status | Public | `/public/visits/:id` | View status | P2 |
