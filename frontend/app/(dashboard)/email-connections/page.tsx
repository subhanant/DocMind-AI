"use client";

import React from "react";
import { Mail, CheckCircle2, Shield, Lock, Clock, Sparkles } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function EmailConnectionsPage() {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          Email Connections
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Connect your business inboxes to automatically detect and ingest PDF/images/DOCX attachments.
        </p>
      </div>

      {/* Security Architecture Banner */}
      <div className="p-4 rounded-xl border border-blue-100 dark:border-blue-900/40 bg-blue-50/60 dark:bg-blue-950/20 text-xs text-slate-700 dark:text-slate-300">
        <div className="flex items-start gap-3">
          <Shield className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-semibold text-slate-900 dark:text-slate-100">
              Enterprise OAuth & Token Security Foundation
            </h4>
            <p className="text-slate-500 dark:text-slate-400 leading-relaxed">
              The underlying database schema (<code className="bg-blue-100/60 dark:bg-blue-900/60 px-1 py-0.5 rounded">email_connections</code>)
              and cryptographic encryption services are established. In Phase 6 (Gmail) and Phase 7 (Microsoft Outlook), OAuth tokens will be encrypted using Argon2/AES-GCM before database storage. Plaintext tokens are strictly forbidden.
            </p>
          </div>
        </div>
      </div>

      {/* Provider Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Gmail Card */}
        <Card className="hover:border-slate-300 dark:hover:border-slate-700 transition-all">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="h-10 w-10 rounded-xl bg-rose-50 dark:bg-rose-950/50 flex items-center justify-center text-rose-600 dark:text-rose-400">
                <Mail className="w-5 h-5" />
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                Phase 6 Roadmap
              </span>
            </div>
            <CardTitle className="text-base font-semibold mt-3">
              Google Gmail
            </CardTitle>
            <CardDescription className="text-xs">
              Connect Google Workspace or Gmail to monitor invoices, bills of lading, and shipping notices.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-0">
            <div className="space-y-2 text-xs text-slate-500 dark:text-slate-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
                <span>Pub/Sub webhook attachment trigger ready</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
                <span>Encrypted token storage model ready</span>
              </div>
            </div>

            <Button variant="outline" disabled className="w-full text-xs">
              <Lock className="w-3.5 h-3.5 mr-1.5" /> Connect Gmail (Phase 6)
            </Button>
          </CardContent>
        </Card>

        {/* Outlook Card */}
        <Card className="hover:border-slate-300 dark:hover:border-slate-700 transition-all">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="h-10 w-10 rounded-xl bg-blue-50 dark:bg-blue-950/50 flex items-center justify-center text-blue-600 dark:text-blue-400">
                <Mail className="w-5 h-5" />
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                Phase 7 Roadmap
              </span>
            </div>
            <CardTitle className="text-base font-semibold mt-3">
              Microsoft Outlook 365
            </CardTitle>
            <CardDescription className="text-xs">
              Connect Microsoft 365 Exchange mailboxes for automatic attachment parsing and ingestion.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-0">
            <div className="space-y-2 text-xs text-slate-500 dark:text-slate-400">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
                <span>Microsoft Graph API attachment pipeline ready</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-500" />
                <span>Multi-tenant enterprise permissions ready</span>
              </div>
            </div>

            <Button variant="outline" disabled className="w-full text-xs">
              <Lock className="w-3.5 h-3.5 mr-1.5" /> Connect Outlook (Phase 7)
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Conceptual Pipeline Visualization */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">
            Automated Ingestion Pipeline (Future Phases)
          </CardTitle>
          <CardDescription className="text-xs">
            How incoming email attachments will flow cleanly through the DocuMind processor
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 text-xs font-mono text-slate-700 dark:text-slate-300 overflow-x-auto">
            Email Inbox → EmailConnector → AttachmentService → DocumentProcessor → Storage → Classifier → OCR → SchemaSelector → LLMExtractor → Validator → Database → Notification
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
