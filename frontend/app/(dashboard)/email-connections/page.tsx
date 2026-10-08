"use client";

import React from "react";
import { ArrowRight, Lock, Mail, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { Reveal } from "@/components/motion/reveal";

const PROVIDERS = [
  {
    name: "Google Gmail",
    description:
      "Monitor a Gmail or Google Workspace inbox for invoices, bills of lading and shipping notices.",
    phase: "Phase 6",
    tone: "bg-rose-50 text-rose-600 dark:bg-rose-950/50 dark:text-rose-400",
    features: [
      "Pub/Sub webhook attachment trigger ready",
      "Encrypted token storage model ready",
    ],
  },
  {
    name: "Microsoft Outlook 365",
    description:
      "Connect Microsoft 365 Exchange mailboxes for automatic attachment parsing and ingestion.",
    phase: "Phase 7",
    tone: "bg-brand-50 text-brand-600 dark:bg-brand-950/50 dark:text-brand-300",
    features: [
      "Microsoft Graph API attachment pipeline ready",
      "Multi-tenant enterprise permissions ready",
    ],
  },
];

const PIPELINE = [
  "Email inbox",
  "Connector",
  "Attachment service",
  "Classifier",
  "OCR",
  "LLM extractor",
  "Validator",
  "Database",
];

export default function EmailConnectionsPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        eyebrow="Automations"
        title="Email connections"
        description="Connect business inboxes so DocMind AI can detect and ingest PDF, image and DOCX attachments automatically."
      />

      <Alert variant="info" title="OAuth & token security foundation">
        The underlying database schema and encryption services are already provisioned. When
        Gmail (Phase 6) and Outlook (Phase 7) land, OAuth tokens will be encrypted before
        storage — plaintext tokens are never persisted.
      </Alert>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {PROVIDERS.map((provider, providerIndex) => (
          /* `interactive` owns the hover transform, so the entrance lives on a
             wrapper instead of the card itself. */
          <Reveal
            key={provider.name}
            index={providerIndex + 1}
            className="h-full"
          >
            <Card interactive className="flex flex-col overflow-hidden">
              <div className="flex items-start justify-between gap-3 p-5 pb-4">
                <span
                  className={`flex h-11 w-11 items-center justify-center rounded-xl [&_svg]:size-5 ${provider.tone}`}
                >
                  <Mail />
                </span>
                <Badge variant="neutral" size="sm">
                  {provider.phase}
                </Badge>
              </div>

              <div className="flex-1 px-5">
                <h2 className="text-base font-semibold text-ink">{provider.name}</h2>
                <p className="mt-1.5 text-xs leading-relaxed text-ink-muted">
                  {provider.description}
                </p>

                <ul className="mt-4 space-y-2">
                  {provider.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-xs text-ink-muted">
                      <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand-500" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-5 pt-5">
                <Button variant="outline" disabled className="w-full">
                  <Lock className="h-3.5 w-3.5" />
                  Connect {provider.name.split(" ").slice(-1)} ({provider.phase})
                </Button>
              </div>
            </Card>
          </Reveal>
        ))}
      </div>

      <Reveal index={3}>
        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4">
            <h2 className="text-sm font-semibold text-ink">Automated ingestion pipeline</h2>
            <p className="mt-0.5 text-xs text-ink-subtle">
              How incoming attachments will flow through the DocMind processor
            </p>
          </div>
          <div className="p-5">
            <div className="flex flex-wrap items-center gap-1.5">
              {PIPELINE.map((stage, index) => (
                <React.Fragment key={stage}>
                  <span className="rounded-lg border border-line bg-surface-muted px-2.5 py-1 text-[11px] font-medium text-ink-muted">
                    {stage}
                  </span>
                  {index < PIPELINE.length - 1 && (
                    <ArrowRight className="h-3 w-3 shrink-0 text-ink-subtle" aria-hidden />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </Card>
      </Reveal>
    </div>
  );
}
