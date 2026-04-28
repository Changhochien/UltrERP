import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { SectionCard, SurfaceMessage } from "../../components/layout/PageLayout";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Checkbox } from "../../components/ui/checkbox";
import { Field, FieldError, FieldLabel } from "../../components/ui/field";
import { Input } from "../../components/ui/input";
import { Skeleton } from "../../components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { useOptionalAuth } from "../../hooks/useAuth";
import { useToast } from "../../hooks/useToast";
import {
  createCurrency,
  createExchangeRate,
  listCurrencies,
  listExchangeRates,
  setBaseCurrency,
  updateCurrency,
  updateExchangeRate,
  type CurrencyRecord,
  type ExchangeRateRecord,
} from "../../lib/api/currencies";

const SELECT_CLASS_NAME =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

interface CurrencyDraft {
  symbol: string;
  decimalPlaces: string;
  isActive: boolean;
}

interface ExchangeRateDraft {
  rate: string;
  rateSource: string;
  isActive: boolean;
}

interface CurrencyFormState {
  code: string;
  symbol: string;
  decimalPlaces: string;
  isActive: boolean;
  isBaseCurrency: boolean;
}

interface ExchangeRateFormState {
  sourceCurrencyCode: string;
  targetCurrencyCode: string;
  effectiveDate: string;
  rate: string;
  rateSource: string;
}

const EMPTY_CURRENCY_FORM: CurrencyFormState = {
  code: "",
  symbol: "",
  decimalPlaces: "2",
  isActive: true,
  isBaseCurrency: false,
};

const EMPTY_EXCHANGE_RATE_FORM: ExchangeRateFormState = {
  sourceCurrencyCode: "",
  targetCurrencyCode: "",
  effectiveDate: "",
  rate: "",
  rateSource: "manual",
};

function normalizeCurrencyCode(value: string): string {
  return value.trim().toUpperCase();
}

function buildCurrencyDrafts(items: CurrencyRecord[]): Record<string, CurrencyDraft> {
  return Object.fromEntries(
    items.map((item) => [
      item.id,
      {
        symbol: item.symbol,
        decimalPlaces: String(item.decimal_places),
        isActive: item.is_active,
      },
    ]),
  );
}

function buildExchangeRateDrafts(items: ExchangeRateRecord[]): Record<string, ExchangeRateDraft> {
  return Object.fromEntries(
    items.map((item) => [
      item.id,
      {
        rate: item.rate,
        rateSource: item.rate_source ?? "",
        isActive: item.is_active,
      },
    ]),
  );
}

async function loadCurrencyMasters(): Promise<{
  currencies: CurrencyRecord[];
  rates: ExchangeRateRecord[];
}> {
  const [currenciesResponse, exchangeRateResponse] = await Promise.all([
    listCurrencies({ pageSize: 200, activeOnly: false }),
    listExchangeRates({ pageSize: 200, activeOnly: false }),
  ]);
  return {
    currencies: currenciesResponse.items,
    rates: exchangeRateResponse.items,
  };
}

function CurrencyMastersLoading() {
  return (
    <div className="space-y-6">
      <SectionCard>
        <div className="space-y-3">
          <Skeleton className="h-10 w-full rounded-xl" />
          <Skeleton className="h-40 w-full rounded-2xl" />
        </div>
      </SectionCard>
      <SectionCard>
        <div className="space-y-3">
          <Skeleton className="h-10 w-full rounded-xl" />
          <Skeleton className="h-40 w-full rounded-2xl" />
        </div>
      </SectionCard>
    </div>
  );
}

export function CurrencyMastersPanel() {
  const { t } = useTranslation("common");
  const auth = useOptionalAuth();
  const { success: showSuccessToast, error: showErrorToast } = useToast();
  const canEdit = auth?.user ? ["owner", "admin", "finance"].includes(auth.user.role) : true;

  const [currencies, setCurrencies] = useState<CurrencyRecord[]>([]);
  const [exchangeRates, setExchangeRates] = useState<ExchangeRateRecord[]>([]);
  const [currencyDrafts, setCurrencyDrafts] = useState<Record<string, CurrencyDraft>>({});
  const [exchangeRateDrafts, setExchangeRateDrafts] = useState<Record<string, ExchangeRateDraft>>({});
  const [newCurrency, setNewCurrency] = useState<CurrencyFormState>(EMPTY_CURRENCY_FORM);
  const [newExchangeRate, setNewExchangeRate] = useState<ExchangeRateFormState>(EMPTY_EXCHANGE_RATE_FORM);
  const [loading, setLoading] = useState(true);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [currencyError, setCurrencyError] = useState<string | null>(null);
  const [exchangeRateError, setExchangeRateError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setLoadingError(null);
    try {
      const data = await loadCurrencyMasters();
      setCurrencies(data.currencies);
      setExchangeRates(data.rates);
      setCurrencyDrafts(buildCurrencyDrafts(data.currencies));
      setExchangeRateDrafts(buildExchangeRateDrafts(data.rates));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load currency masters";
      setLoadingError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const activeCurrencies = currencies.filter((currency) => currency.is_active);

  async function handleCreateCurrency() {
    const code = normalizeCurrencyCode(newCurrency.code);
    const symbol = newCurrency.symbol.trim();
    const decimalPlaces = Number(newCurrency.decimalPlaces);

    if (code.length !== 3) {
      setCurrencyError("Currency code must be exactly 3 characters.");
      return;
    }
    if (!symbol) {
      setCurrencyError("Currency symbol is required.");
      return;
    }
    if (!Number.isInteger(decimalPlaces) || decimalPlaces < 0 || decimalPlaces > 6) {
      setCurrencyError("Decimal places must be an integer between 0 and 6.");
      return;
    }

    setCurrencyError(null);
    setSavingKey("new-currency");
    try {
      await createCurrency({
        code,
        symbol,
        decimal_places: decimalPlaces,
        is_active: newCurrency.isActive,
        is_base_currency: newCurrency.isBaseCurrency,
      });
      showSuccessToast("Currency saved", `${code} is now available for finance workflows.`);
      setNewCurrency(EMPTY_CURRENCY_FORM);
      await refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to create currency";
      setCurrencyError(message);
      showErrorToast("Currency save failed", message);
    } finally {
      setSavingKey(null);
    }
  }

  async function handleSaveCurrency(currency: CurrencyRecord) {
    const draft = currencyDrafts[currency.id];
    if (!draft) {
      return;
    }

    const symbol = draft.symbol.trim();
    const decimalPlaces = Number(draft.decimalPlaces);
    if (!symbol) {
      setCurrencyError(`Currency symbol is required for ${currency.code}.`);
      return;
    }
    if (!Number.isInteger(decimalPlaces) || decimalPlaces < 0 || decimalPlaces > 6) {
      setCurrencyError(`Decimal places for ${currency.code} must be between 0 and 6.`);
      return;
    }
    if (currency.is_base_currency && !draft.isActive) {
      setCurrencyError("Base currency cannot be inactive.");
      return;
    }

    setCurrencyError(null);
    setSavingKey(`currency:${currency.id}`);
    try {
      await updateCurrency(currency.id, {
        symbol,
        decimal_places: decimalPlaces,
        is_active: draft.isActive,
      });
      showSuccessToast("Currency updated", `${currency.code} master data was updated.`);
      await refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update currency";
      setCurrencyError(message);
      showErrorToast("Currency update failed", message);
    } finally {
      setSavingKey(null);
    }
  }

  async function handleMakeBase(currency: CurrencyRecord) {
    setCurrencyError(null);
    setSavingKey(`base:${currency.id}`);
    try {
      await setBaseCurrency(currency.id);
      showSuccessToast("Base currency updated", `${currency.code} is now the tenant base currency.`);
      await refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update base currency";
      setCurrencyError(message);
      showErrorToast("Base currency update failed", message);
    } finally {
      setSavingKey(null);
    }
  }

  async function handleCreateExchangeRate() {
    const sourceCurrencyCode = normalizeCurrencyCode(newExchangeRate.sourceCurrencyCode);
    const targetCurrencyCode = normalizeCurrencyCode(newExchangeRate.targetCurrencyCode);
    const rate = newExchangeRate.rate.trim();
    const effectiveDate = newExchangeRate.effectiveDate;

    if (!sourceCurrencyCode || !targetCurrencyCode) {
      setExchangeRateError("Select both source and target currencies.");
      return;
    }
    if (sourceCurrencyCode === targetCurrencyCode) {
      setExchangeRateError("Source and target currencies must differ.");
      return;
    }
    if (!effectiveDate) {
      setExchangeRateError("Effective date is required.");
      return;
    }
    if (!rate || Number(rate) <= 0) {
      setExchangeRateError("Exchange rate must be greater than zero.");
      return;
    }

    const duplicateRate = exchangeRates.some(
      (item) =>
        item.source_currency_code === sourceCurrencyCode
        && item.target_currency_code === targetCurrencyCode
        && item.effective_date === effectiveDate,
    );
    if (duplicateRate) {
      setExchangeRateError("An exchange rate already exists for this pair and effective date.");
      return;
    }

    setExchangeRateError(null);
    setSavingKey("new-rate");
    try {
      await createExchangeRate({
        source_currency_code: sourceCurrencyCode,
        target_currency_code: targetCurrencyCode,
        effective_date: effectiveDate,
        rate,
        rate_source: newExchangeRate.rateSource.trim() || null,
      });
      showSuccessToast(
        "Exchange rate saved",
        `${sourceCurrencyCode} to ${targetCurrencyCode} is available for dated lookups.`,
      );
      setNewExchangeRate(EMPTY_EXCHANGE_RATE_FORM);
      await refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to create exchange rate";
      setExchangeRateError(message);
      showErrorToast("Exchange rate save failed", message);
    } finally {
      setSavingKey(null);
    }
  }

  async function handleSaveExchangeRate(rateRecord: ExchangeRateRecord) {
    const draft = exchangeRateDrafts[rateRecord.id];
    if (!draft) {
      return;
    }

    const rate = draft.rate.trim();
    if (!rate || Number(rate) <= 0) {
      setExchangeRateError(`Exchange rate for ${rateRecord.source_currency_code}/${rateRecord.target_currency_code} must be greater than zero.`);
      return;
    }

    setExchangeRateError(null);
    setSavingKey(`rate:${rateRecord.id}`);
    try {
      await updateExchangeRate(rateRecord.id, {
        rate,
        rate_source: draft.rateSource.trim() || null,
        is_active: draft.isActive,
      });
      showSuccessToast(
        "Exchange rate updated",
        `${rateRecord.source_currency_code} to ${rateRecord.target_currency_code} was updated.`,
      );
      await refresh();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to update exchange rate";
      setExchangeRateError(message);
      showErrorToast("Exchange rate update failed", message);
    } finally {
      setSavingKey(null);
    }
  }

  if (loading) {
    return <CurrencyMastersLoading />;
  }

  return (
    <div className="space-y-6">
      {!canEdit ? (
        <SurfaceMessage tone="warning">
          {t("settingsPage.currencyMasters.readOnly", {
            defaultValue: "Your role can view currency masters but cannot edit them.",
          })}
        </SurfaceMessage>
      ) : null}

      {loadingError ? <SurfaceMessage tone="danger">{loadingError}</SurfaceMessage> : null}

      <SectionCard
        title={t("settingsPage.currencyMasters.currenciesTitle", { defaultValue: "Currencies" })}
        description={t("settingsPage.currencyMasters.currenciesDescription", {
          defaultValue: "Maintain supported currencies, precision, active state, and the single base currency.",
        })}
      >
        <div className="space-y-4">
          <div className="grid gap-3 rounded-xl border border-dashed border-border/70 bg-muted/20 p-4 md:grid-cols-[110px_minmax(0,1fr)_120px_auto_auto_auto] md:items-end">
            <Field>
              <FieldLabel htmlFor="new-currency-code">Code</FieldLabel>
              <Input
                id="new-currency-code"
                value={newCurrency.code}
                onChange={(event) => setNewCurrency((current) => ({ ...current, code: event.target.value }))}
                maxLength={3}
                disabled={!canEdit}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="new-currency-symbol">Symbol</FieldLabel>
              <Input
                id="new-currency-symbol"
                value={newCurrency.symbol}
                onChange={(event) => setNewCurrency((current) => ({ ...current, symbol: event.target.value }))}
                disabled={!canEdit}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="new-currency-precision">Decimal places</FieldLabel>
              <Input
                id="new-currency-precision"
                type="number"
                min="0"
                max="6"
                value={newCurrency.decimalPlaces}
                onChange={(event) => setNewCurrency((current) => ({ ...current, decimalPlaces: event.target.value }))}
                disabled={!canEdit}
              />
            </Field>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <Checkbox
                checked={newCurrency.isActive}
                onCheckedChange={(checked) => setNewCurrency((current) => ({ ...current, isActive: Boolean(checked) }))}
                disabled={!canEdit}
                aria-label="New currency active"
              />
              Active
            </label>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <Checkbox
                checked={newCurrency.isBaseCurrency}
                onCheckedChange={(checked) => setNewCurrency((current) => ({ ...current, isBaseCurrency: Boolean(checked) }))}
                disabled={!canEdit}
                aria-label="New currency base"
              />
              Base
            </label>
            <Button type="button" onClick={handleCreateCurrency} disabled={!canEdit || savingKey === "new-currency"}>
              {savingKey === "new-currency" ? "Saving…" : "Add currency"}
            </Button>
          </div>

          {currencyError ? <FieldError>{currencyError}</FieldError> : null}

          {currencies.length === 0 ? (
            <SurfaceMessage tone="default">
              {t("settingsPage.currencyMasters.noCurrencies", {
                defaultValue: "No currencies are available yet.",
              })}
            </SurfaceMessage>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Decimal places</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Base</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {currencies.map((currency) => {
                  const draft = currencyDrafts[currency.id] ?? {
                    symbol: currency.symbol,
                    decimalPlaces: String(currency.decimal_places),
                    isActive: currency.is_active,
                  };
                  return (
                    <TableRow key={currency.id}>
                      <TableCell className="font-medium">{currency.code}</TableCell>
                      <TableCell>
                        <Input
                          aria-label={`Symbol for ${currency.code}`}
                          value={draft.symbol}
                          onChange={(event) => setCurrencyDrafts((current) => ({
                            ...current,
                            [currency.id]: { ...draft, symbol: event.target.value },
                          }))}
                          disabled={!canEdit}
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          aria-label={`Decimal places for ${currency.code}`}
                          type="number"
                          min="0"
                          max="6"
                          value={draft.decimalPlaces}
                          onChange={(event) => setCurrencyDrafts((current) => ({
                            ...current,
                            [currency.id]: { ...draft, decimalPlaces: event.target.value },
                          }))}
                          disabled={!canEdit}
                        />
                      </TableCell>
                      <TableCell>
                        <label className="flex items-center gap-2 text-sm text-foreground">
                          <Checkbox
                            checked={draft.isActive}
                            onCheckedChange={(checked) => setCurrencyDrafts((current) => ({
                              ...current,
                              [currency.id]: { ...draft, isActive: Boolean(checked) },
                            }))}
                            disabled={!canEdit || currency.is_base_currency}
                            aria-label={`Active ${currency.code}`}
                          />
                          {draft.isActive ? "Active" : "Inactive"}
                        </label>
                      </TableCell>
                      <TableCell>
                        {currency.is_base_currency ? <Badge variant="info">Base</Badge> : <Badge variant="outline">Standard</Badge>}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => void handleSaveCurrency(currency)}
                            disabled={!canEdit || savingKey === `currency:${currency.id}`}
                          >
                            {savingKey === `currency:${currency.id}` ? "Saving…" : "Save"}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => void handleMakeBase(currency)}
                            disabled={!canEdit || currency.is_base_currency || savingKey === `base:${currency.id}`}
                          >
                            {savingKey === `base:${currency.id}` ? "Saving…" : "Make base"}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </div>
      </SectionCard>

      <SectionCard
        title={t("settingsPage.currencyMasters.exchangeRatesTitle", { defaultValue: "Exchange rates" })}
        description={t("settingsPage.currencyMasters.exchangeRatesDescription", {
          defaultValue: "Maintain effective-dated rates without recomputing historical document snapshots.",
        })}
      >
        <div className="space-y-4">
          <div className="grid gap-3 rounded-xl border border-dashed border-border/70 bg-muted/20 p-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_150px_140px_minmax(0,1fr)_auto] md:items-end">
            <Field>
              <FieldLabel htmlFor="new-rate-source">Source currency</FieldLabel>
              <select
                id="new-rate-source"
                className={SELECT_CLASS_NAME}
                aria-label="New exchange rate source currency"
                value={newExchangeRate.sourceCurrencyCode}
                onChange={(event) => setNewExchangeRate((current) => ({ ...current, sourceCurrencyCode: event.target.value }))}
                disabled={!canEdit}
              >
                <option value="">{t("selectCurrency")}</option>
                {activeCurrencies.map((currency) => (
                  <option key={currency.id} value={currency.code}>{currency.code}</option>
                ))}
              </select>
            </Field>
            <Field>
              <FieldLabel htmlFor="new-rate-target">Target currency</FieldLabel>
              <select
                id="new-rate-target"
                className={SELECT_CLASS_NAME}
                aria-label="New exchange rate target currency"
                value={newExchangeRate.targetCurrencyCode}
                onChange={(event) => setNewExchangeRate((current) => ({ ...current, targetCurrencyCode: event.target.value }))}
                disabled={!canEdit}
              >
                <option value="">{t("selectCurrency")}</option>
                {activeCurrencies.map((currency) => (
                  <option key={currency.id} value={currency.code}>{currency.code}</option>
                ))}
              </select>
            </Field>
            <Field>
              <FieldLabel htmlFor="new-rate-effective-date">Effective date</FieldLabel>
              <Input
                id="new-rate-effective-date"
                aria-label="New exchange rate effective date"
                type="date"
                value={newExchangeRate.effectiveDate}
                onChange={(event) => setNewExchangeRate((current) => ({ ...current, effectiveDate: event.target.value }))}
                disabled={!canEdit}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="new-rate-value">Rate</FieldLabel>
              <Input
                id="new-rate-value"
                aria-label="New exchange rate value"
                value={newExchangeRate.rate}
                onChange={(event) => setNewExchangeRate((current) => ({ ...current, rate: event.target.value }))}
                disabled={!canEdit}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="new-rate-source-note">Rate source</FieldLabel>
              <Input
                id="new-rate-source-note"
                aria-label="New exchange rate source note"
                value={newExchangeRate.rateSource}
                onChange={(event) => setNewExchangeRate((current) => ({ ...current, rateSource: event.target.value }))}
                disabled={!canEdit}
              />
            </Field>
            <Button type="button" onClick={handleCreateExchangeRate} disabled={!canEdit || savingKey === "new-rate"}>
              {savingKey === "new-rate" ? "Saving…" : "Add rate"}
            </Button>
          </div>

          {exchangeRateError ? <FieldError>{exchangeRateError}</FieldError> : null}

          {exchangeRates.length === 0 ? (
            <SurfaceMessage tone="default">
              {t("settingsPage.currencyMasters.noRates", {
                defaultValue: "No exchange rates are available yet.",
              })}
            </SurfaceMessage>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Pair</TableHead>
                  <TableHead>Effective date</TableHead>
                  <TableHead>Rate</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {exchangeRates.map((rateRecord) => {
                  const draft = exchangeRateDrafts[rateRecord.id] ?? {
                    rate: rateRecord.rate,
                    rateSource: rateRecord.rate_source ?? "",
                    isActive: rateRecord.is_active,
                  };
                  const label = `${rateRecord.source_currency_code} to ${rateRecord.target_currency_code} on ${rateRecord.effective_date}`;
                  return (
                    <TableRow key={rateRecord.id}>
                      <TableCell className="font-medium">{rateRecord.source_currency_code} → {rateRecord.target_currency_code}</TableCell>
                      <TableCell>{rateRecord.effective_date}</TableCell>
                      <TableCell>
                        <Input
                          aria-label={`Rate for ${label}`}
                          value={draft.rate}
                          onChange={(event) => setExchangeRateDrafts((current) => ({
                            ...current,
                            [rateRecord.id]: { ...draft, rate: event.target.value },
                          }))}
                          disabled={!canEdit}
                        />
                      </TableCell>
                      <TableCell>
                        <Input
                          aria-label={`Rate source for ${label}`}
                          value={draft.rateSource}
                          onChange={(event) => setExchangeRateDrafts((current) => ({
                            ...current,
                            [rateRecord.id]: { ...draft, rateSource: event.target.value },
                          }))}
                          disabled={!canEdit}
                        />
                      </TableCell>
                      <TableCell>
                        <label className="flex items-center gap-2 text-sm text-foreground">
                          <Checkbox
                            checked={draft.isActive}
                            onCheckedChange={(checked) => setExchangeRateDrafts((current) => ({
                              ...current,
                              [rateRecord.id]: { ...draft, isActive: Boolean(checked) },
                            }))}
                            disabled={!canEdit}
                            aria-label={`Active ${label}`}
                          />
                          {draft.isActive ? "Active" : "Inactive"}
                        </label>
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => void handleSaveExchangeRate(rateRecord)}
                            disabled={!canEdit || savingKey === `rate:${rateRecord.id}`}
                          >
                            {savingKey === `rate:${rateRecord.id}` ? "Saving…" : "Save"}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

export default CurrencyMastersPanel;