/**
 * Collections Page (Epic 26 - Story 26-5)
 * Manual dunning and collections tracking
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { CheckCircle, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface DunningNotice {
  id: string;
  notice_number: string;
  notice_date: string;
  status: string;
  customer_name: string;
  invoice_number: string;
  outstanding_amount: string;
  fee_amount: string;
  total_amount: string;
  reminder_level: number;
}

interface OverdueInvoice {
  id: string;
  invoice_number: string;
  customer_name: string;
  invoice_date: string;
  due_date: string;
  total_amount: string;
  outstanding_amount: string;
}

export function CollectionsPage() {
  const { t } = useTranslation("payments");
  const [notices, setNotices] = useState<DunningNotice[]>([]);
  const [overdueInvoices] = useState<OverdueInvoice[]>([]);
  const [activeTab, setActiveTab] = useState("notices");

  const loadNotices = async () => {
    try {
      const response = await fetch("/api/v1/accounting/dunning-notices", {
        headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
      });
      if (response.ok) {
        const data = await response.json();
        setNotices(data);
      }
    } catch (error) {
      console.error("Failed to load notices:", error);
    }
  };

  const handleTransition = async (noticeId: string, newStatus: string) => {
    try {
      const response = await fetch(`/api/v1/accounting/dunning-notices/${noticeId}/transition`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("token")}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ status: newStatus })
      });

      if (response.ok) {
        loadNotices();
      }
    } catch (error) {
      console.error("Failed to update notice:", error);
    }
  };

  const draftCount = notices.filter(n => n.status === "draft").length;
  const openCount = notices.filter(n => n.status === "open").length;
  const resolvedCount = notices.filter(n => n.status === "resolved").length;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "draft":
        return <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800">{t("collections.statusDraft")}</span>;
      case "open":
        return <span className="inline-flex items-center rounded-full bg-orange-100 px-2 py-1 text-xs font-medium text-orange-800">{t("collections.statusOpen")}</span>;
      case "resolved":
        return <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">{t("collections.statusResolved")}</span>;
      case "cancelled":
        return <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-800">{t("collections.statusCancelled")}</span>;
      default:
        return <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t("routes.collections.label", { defaultValue: "Collections" })}
          </h1>
          <p className="text-muted-foreground">
            {t("routes.collections.description", { defaultValue: "Track overdue invoices and dunning notices" })}
          </p>
        </div>
        <Button onClick={loadNotices} variant="outline" size="sm">
          {t("collections.refresh")}
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t("collections.draftNotices")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-gray-600">{draftCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t("collections.openNotices")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{openCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t("collections.resolved")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{resolvedCount}</div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="notices">{t("collections.dunningNotices")}</TabsTrigger>
          <TabsTrigger value="overdue">{t("collections.overdueInvoices")}</TabsTrigger>
        </TabsList>

        <TabsContent value="notices" className="space-y-4">
          <div className="rounded-md border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-2 text-left text-sm font-medium">{t("collections.noticeNumber")}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium">{t("collections.date")}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium">{t("collections.customer")}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium">{t("collections.invoice")}</th>
                  <th className="px-4 py-2 text-right text-sm font-medium">{t("collections.amount")}</th>
                  <th className="px-4 py-2 text-center text-sm font-medium">{t("collections.status")}</th>
                  <th className="px-4 py-2 text-center text-sm font-medium">{t("collections.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {notices.map((notice) => (
                  <tr key={notice.id} className="border-b">
                    <td className="px-4 py-2 text-sm font-mono">{notice.notice_number}</td>
                    <td className="px-4 py-2 text-sm">{notice.notice_date}</td>
                    <td className="px-4 py-2 text-sm">{notice.customer_name}</td>
                    <td className="px-4 py-2 text-sm">{notice.invoice_number}</td>
                    <td className="px-4 py-2 text-right text-sm">{notice.total_amount}</td>
                    <td className="px-4 py-2 text-center">{getStatusBadge(notice.status)}</td>
                    <td className="px-4 py-2 text-center">
                      {notice.status === "draft" && (
                        <Button size="sm" onClick={() => handleTransition(notice.id, "open")}>
                          <Send className="mr-1 h-3 w-3" />
                          {t("collections.send")}
                        </Button>
                      )}
                      {notice.status === "open" && (
                        <Button size="sm" onClick={() => handleTransition(notice.id, "resolved")}>
                          <CheckCircle className="mr-1 h-3 w-3" />
                          {t("collections.resolve")}
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
                {notices.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                      {t("collections.noDunningNotices")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </TabsContent>

        <TabsContent value="overdue">
          <div className="rounded-md border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-2 text-left text-sm font-medium">{t("collections.invoiceNumber")}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium">{t("collections.customer")}</th>
                  <th className="px-4 py-2 text-left text-sm font-medium">{t("collections.date")}</th>
                  <th className="px-4 py-2 text-right text-sm font-medium">{t("collections.amount")}</th>
                  <th className="px-4 py-2 text-right text-sm font-medium">{t("collections.outstanding")}</th>
                </tr>
              </thead>
              <tbody>
                {overdueInvoices.map((invoice) => (
                  <tr key={invoice.id} className="border-b">
                    <td className="px-4 py-2 text-sm font-mono">{invoice.invoice_number}</td>
                    <td className="px-4 py-2 text-sm">{invoice.customer_name}</td>
                    <td className="px-4 py-2 text-sm">{invoice.invoice_date}</td>
                    <td className="px-4 py-2 text-right text-sm">{invoice.total_amount}</td>
                    <td className="px-4 py-2 text-right text-sm text-red-600">{invoice.outstanding_amount}</td>
                  </tr>
                ))}
                {overdueInvoices.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                      {t("collections.noOverdueInvoices")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
