import type { Product } from '../generated/schemas';
import { formatCurrency } from '../lib/format';
import type { LineErrors } from '../lib/validators';
import { MAX_LINE_QUANTITY } from '../lib/validators';

export interface DraftLine {
  key: number;
  sku: string;
  quantity: string;
}

export interface OrderLineEditorProps {
  index: number;
  line: DraftLine;
  products: readonly Product[];
  errors?: LineErrors | undefined;
  canRemove: boolean;
  onChange: (line: DraftLine) => void;
  onRemove: () => void;
}

export function OrderLineEditor({ index, line, products, errors, canRemove, onChange, onRemove }: OrderLineEditorProps) {
  const n = index + 1;
  const product = products.find((p) => p.sku === line.sku);
  const skuErrorId = `line-${line.key}-sku-error`;
  const qtyErrorId = `line-${line.key}-qty-error`;
  return (
    <fieldset className="line-editor" data-testid="order-line">
      <legend>Line {n}</legend>
      <label>
        Product for line {n}
        <select
          value={line.sku}
          aria-invalid={errors?.sku ? true : undefined}
          aria-describedby={errors?.sku ? skuErrorId : undefined}
          onChange={(e) => onChange({ ...line, sku: e.target.value })}
        >
          <option value="">Select a product</option>
          {products.map((p) => (
            <option key={p.sku} value={p.sku}>
              {p.sku} &mdash; {p.name} ({formatCurrency(p.unitPrice)})
            </option>
          ))}
        </select>
      </label>
      {errors?.sku && (
        <span id={skuErrorId} className="field-error">
          {errors.sku}
        </span>
      )}
      <label>
        Quantity for line {n}
        <input
          type="number"
          inputMode="numeric"
          min={1}
          max={MAX_LINE_QUANTITY}
          value={line.quantity}
          aria-invalid={errors?.quantity ? true : undefined}
          aria-describedby={errors?.quantity ? qtyErrorId : undefined}
          onChange={(e) => onChange({ ...line, quantity: e.target.value })}
        />
      </label>
      {errors?.quantity && (
        <span id={qtyErrorId} className="field-error">
          {errors.quantity}
        </span>
      )}
      <span className="line-price" aria-label={`Line ${n} amount`}>
        {product && /^\d+$/.test(line.quantity) ? formatCurrency(product.unitPrice * Number(line.quantity)) : '—'}
      </span>
      <button type="button" onClick={onRemove} disabled={!canRemove} aria-label={`Remove line ${n}`}>
        Remove
      </button>
    </fieldset>
  );
}
