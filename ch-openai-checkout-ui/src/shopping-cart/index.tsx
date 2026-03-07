import { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { useOpenAiGlobal } from "../use-openai-global";
import { useWidgetState } from "../use-widget-state";
// import { CallToolResponse } from "src/types";
// import { QuadraticBezierCurve } from "three";

type Item = {
  id: string;
  name: string;
  description: string;
  imageURL?: string;
  Icon?: React.ComponentType<React.SVGProps<SVGSVGElement>>;
};

type CartItem = {
  id: string;
  quantity: number;
  [key: string]: unknown;
};

type CartWidgetState = {
  cartId?: string;
  items?: CartItem[];
  [key: string]: unknown;
};

const createDefaultCartState = (): CartWidgetState => ({
  items: [],
});

function usePrettyJson(value: unknown): string {
  return useMemo(() => {
    if (value === undefined || value === null) {
      return "null";
    }

    try {
      return JSON.stringify(value, null, 2);
    } catch (error) {
      return `<<unable to render: ${error}>>`;
    }
  }, [value]);
}

function JsonPanel({ label, value }: { label: string; value: unknown }) {
  const pretty = usePrettyJson(value);

  return (
    <section className="rounded-2xl border border-black/20 bg-[#fffaf5] p-4">
      <header className="mb-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-black/60">
          {label}
        </p>
      </header>
      <pre className="max-h-64 overflow-auto rounded-xl bg-white p-3 font-mono text-xs text-black/70 shadow-sm">
        {pretty}
      </pre>
    </section>
  );
}

function App() {
  const toolOutput = useOpenAiGlobal("toolOutput");
  const toolResponseMetadata = useOpenAiGlobal("toolResponseMetadata");
  const widgetState = useOpenAiGlobal("widgetState");
  const [suggestedItems, setSuggestedItems] = useState<Item[]>([]);
  const [cartState, setCartState] = useWidgetState<CartWidgetState>(
    createDefaultCartState
  );
  const cartItems = Array.isArray(cartState?.items) ? cartState.items : [];
  const [currentPage, setCurrentPage] = useState<"main" | "checkout" | "receipt">("main");
  const [checkoutItems, setCheckoutItems] = useState<CartItem[]>([]);
  const [checkoutSessionPayload, setCheckoutSessionPayload] = useState<any>(null);
  const [orderResponse, setOrderResponse] = useState<any>(null);
  const animationStyles = `
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `;

  function addItem(id: string) {
    if (!id) {
      return;
    }

    setCartState((prevState) => {
      const baseState: CartWidgetState = prevState ?? {};
      const items = Array.isArray(baseState.items)
        ? baseState.items.map((item) => ({ ...item }))
        : [];
      const idx = items.findIndex((item) => item.id === id);

      if (idx === -1) {
        items.push({ id, quantity: 1 });
      } else {
        const current = items[idx];
        items[idx] = {
          ...current,
          quantity: (current.quantity ?? 0) + 1,
        };
      }

      return { ...baseState, items };
    });
  }

  function adjustQuantity(id: string, delta: number) {
    if (!id || delta === 0) {
      return;
    }

    console.log("adjustQuantity", { id, delta });
    setCartState((prevState) => {
      const baseState: CartWidgetState = prevState ?? {};
      const items = Array.isArray(baseState.items)
        ? baseState.items.map((item) => ({ ...item }))
        : [];
      console.log("adjustQuantity:prev", baseState);

      const idx = items.findIndex((item) => item.id === id);
      if (idx === -1) {
        console.log("adjustQuantity:missing", id);
        return baseState;
      }

      const current = items[idx];
      const nextQuantity = Math.max(0, (current.quantity ?? 0) + delta);
      if (nextQuantity === 0) {
        items.splice(idx, 1);
      } else {
        items[idx] = { ...current, quantity: nextQuantity };
      }

      const nextState = { ...baseState, items };
      console.log("adjustQuantity:next", nextState);
      return nextState;
    });
  }

  const lastToolOutputRef = useRef<string>("__tool_output_unset__");

  useEffect(() => {
    // Merge deltas (toolOutput) into the latest widgetState without
    // and then update cartState. Runs whenever toolOutput changes.
    if (toolOutput == null) {
      return;
    }

    // changes to cartState triggered from UI will also trigger another global update event,
    // so we need to check if the tool event has actually changed.
    const serializedToolOutput = (() => {
      try {
        return JSON.stringify({ toolOutput, toolResponseMetadata });
      } catch (error) {
        console.warn("Unable to serialize toolOutput", error);
        return "__tool_output_error__";
      }
    })();

    if (serializedToolOutput === lastToolOutputRef.current) {
      console.log("useEffect skipped (toolOutput is actually unchanged)");
      return;
    }
    lastToolOutputRef.current = serializedToolOutput;

    // Get the items that the user wants to add to the cart from toolOutput
    const incomingItems = Array.isArray(
      (toolOutput as { items?: unknown } | null)?.items
    )
      ? (toolOutput as { items?: CartItem[] }).items ?? []
      : [];

    // Since we set `widgetSessionId` on the tool response, when the tool response returns
    // widgetState should contain the state from the previous turn of conversation
    // treat widgetState as the definitive local state, and add the new items
    const baseState = widgetState ?? cartState ?? createDefaultCartState();
    const baseItems = Array.isArray(baseState.items) ? baseState.items : [];
    const incomingCartId =
      typeof (toolOutput as { cartId?: unknown } | null)?.cartId === "string"
        ? (toolOutput as { cartId?: string }).cartId ?? undefined
        : undefined;

    const itemsByName = new Map<string, CartItem>();
    for (const item of baseItems) {
      if (item?.name) {
        itemsByName.set(item.name, item);
      }
    }
    // Add in the new items to create newState
    for (const item of incomingItems) {
      if (item?.name) {
        itemsByName.set(item.name, { ...itemsByName.get(item.name), ...item });
      }
    }

    const nextItems = Array.from(itemsByName.values());
    const nextState = {
      ...baseState,
      cartId: baseState.cartId ?? incomingCartId,
      items: nextItems,
    };

    // Update cartState with the new state that includes the new items
    // Updating cartState automatically updates window.openai.widgetState.
    setCartState(nextState as CartWidgetState);

    // populate suggested item from search results
    if ((toolOutput as { results?: unknown }).results) {
      const items: Item[] | undefined = (toolOutput as { results?: { id: string; title: string, description: string, media?: { imageURL?: string } }[] }).results?.map((res) =>{
        return {
          id: res.id,
          name: res.title,
          description: '',
          imageURL: res.media?.imageURL,
        }
      });
      if (items?.length) {
        setSuggestedItems(items.slice(0, 6));
      }
    }
  }, [toolOutput, toolResponseMetadata]);

  async function handleCheckout(sessionJson: string) {
    const session = JSON.parse(sessionJson);

    if (!window.openai?.requestCheckout) {
      throw new Error("requestCheckout is not available in this host");
    }

    // Host opens the Instant Checkout UI.
    const order = await window.openai.requestCheckout(session);
    return order; // host returns the order payload
  }

  async function handlePlaceOrder() {
    
    const orderResult = await handleCheckout(JSON.stringify(checkoutSessionPayload));
    setOrderResponse(orderResult);
    setCurrentPage("receipt");

    // Clear the cart after placing order
    setCartState({ items: [] });
  }

  const submitCheckout = async () => {
    //get checkout session
    const result: CallToolResponse = await window.openai.callTool("get_checkout_session", {
      items: cartItems.map(item => ({
        id: item.id,
        quantity: item.quantity,
      })),
      fulfillment_address: {
        name: "John Doe",
        line_one: "123 Main St",
        line_two: "Apt 4B",
        city: "Anytown",
        state: "CA",
        postal_code: "12345",
        country: "US",
      },
    });
    const resultBody = result.structuredContent;
    setCheckoutSessionPayload(resultBody);

    const newCheckoutItems = resultBody.line_items.map(li => ({
      id: li.id,
      quantity: li.item.quantity,
      price: li.base_amount,
      total: li.total,
    }));
    setCheckoutItems(newCheckoutItems);

    setCurrentPage("checkout");
  };

  if (currentPage === "receipt") {
    const subtotal = (checkoutSessionPayload?.totals?.find((cs: any) => cs.type === 'subtotal')?.amount ?? 0) / 100;
    const tax = (checkoutSessionPayload?.totals?.find((cs: any) => cs.type === 'tax')?.amount ?? 0) / 100;
    const total = (checkoutSessionPayload?.totals?.find((cs: any) => cs.type === 'total')?.amount ?? 0) / 100;
    const orderDate = new Date().toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
    const orderId = orderResponse?.id || `ORDER-${Date.now()}`;

    return (
      <div
        className="min-h-screen w-full bg-white text-black bg-[radial-gradient(circle_at_top_left,_#fff7ed_0,_#ffffff_55%),radial-gradient(circle_at_bottom_right,_#eef2ff_0,_#ffffff_45%)]"
        style={{
          fontFamily: '"Trebuchet MS", "Gill Sans", "Lucida Grande", sans-serif',
        }}
        data-theme="light"
      >
        <style>{animationStyles}</style>
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 px-4 py-8 md:px-6 lg:px-8">
          <header
            className="space-y-4 text-center"
            style={{ animation: "fadeUp 0.6s ease-out both" }}
          >
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-green-100">
              <svg
                className="h-10 w-10 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-green-700">
              Purchase completed!
            </h1>
            <p className="text-sm text-black/70">
              Thank you for your order. Your purchase has been successfully processed.
            </p>
          </header>

          <div
            className="rounded-2xl border border-black/20 bg-[#fffaf5] p-6"
            style={{
              animation: "fadeUp 0.7s ease-out both",
              animationDelay: "80ms",
            }}
          >
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-black/60">Order ID</span>
                <span className="font-mono font-semibold text-black">{orderId}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-black/60">Order Date</span>
                <span className="font-semibold text-black">{orderDate}</span>
              </div>
            </div>
          </div>

          <div
            className="space-y-4"
            style={{
              animation: "fadeUp 0.7s ease-out both",
              animationDelay: "120ms",
            }}
          >
            <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-black/60">
              Order Items
            </h2>
            {checkoutItems.map((item, index) => {
              const price: number = (item.price as number) / 100;
              const itemTotal = (item.total as number) / 100;
              const suggestedItem: Item | undefined = suggestedItems.find((si) => si.id === item.id);

              return (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-2xl border border-black/20 bg-[#fffaf5] p-4"
                  style={{
                    animation: "fadeUp 0.5s ease-out both",
                    animationDelay: `${160 + index * 60}ms`,
                  }}
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-white shadow-sm">
                      <img src={suggestedItem?.imageURL} alt={suggestedItem?.name} className="h-10 w-10" />
                    </div>
                    <div>
                      <p className="text-base font-semibold text-black">
                        {suggestedItem?.name}
                      </p>
                      <p className="text-sm text-black/60">
                        ${price.toFixed(2)} × {item.quantity}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-black">
                      ${itemTotal.toFixed(2)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          <div
            className="space-y-3 rounded-2xl border border-black/20 bg-[#fffaf5] p-6"
            style={{
              animation: "fadeUp 0.7s ease-out both",
              animationDelay: "240ms",
            }}
          >
            <div className="flex justify-between text-base text-black/70">
              <span>Subtotal</span>
              <span className="font-mono">${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-base text-black/70">
              <span>Tax</span>
              <span className="font-mono">${tax.toFixed(2)}</span>
            </div>
            <div className="border-t border-black/20 pt-3">
              <div className="flex justify-between">
                <span className="text-xl font-semibold text-black">Total</span>
                <span className="text-xl font-semibold text-black">
                  ${total.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

        </div>
      </div>
    );
  }

  if (currentPage === "checkout") {
    const subtotal = (checkoutSessionPayload.totals.find((cs: any) => cs.type === 'subtotal')?.amount ?? 0) / 100;
    const tax = (checkoutSessionPayload.totals.find((cs: any) => cs.type === 'tax')?.amount ?? 0) / 100;
    const total = (checkoutSessionPayload.totals.find((cs: any) => cs.type === 'total')?.amount ?? 0) / 100;
    return (
      <div
        className="min-h-screen w-full bg-white text-black bg-[radial-gradient(circle_at_top_left,_#fff7ed_0,_#ffffff_55%),radial-gradient(circle_at_bottom_right,_#eef2ff_0,_#ffffff_45%)]"
        style={{
          fontFamily: '"Trebuchet MS", "Gill Sans", "Lucida Grande", sans-serif',
        }}
        data-theme="light"
      >
        <style>{animationStyles}</style>
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 px-4 py-8 md:px-6 lg:px-8">
          <header
            className="space-y-2"
            style={{ animation: "fadeUp 0.6s ease-out both" }}
          >
            <button
              type="button"
              onClick={() => setCurrentPage("main")}
              className="mb-4 flex items-center gap-2 text-sm font-semibold text-black/70 transition hover:text-black"
            >
              <span className="text-xl">←</span> Back to cart
            </button>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-black/60">
              Checkout
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">
              Review your order
            </h1>
            <p className="text-sm text-black/70">
              Confirm your items and complete your purchase
            </p>
          </header>

          <div
            className="space-y-4"
            style={{
              animation: "fadeUp 0.7s ease-out both",
              animationDelay: "80ms",
            }}
          >
            {checkoutItems.map((item, index) => {
              const price: number = (item.price as number) / 100;
              const itemTotal = (item.total as number) / 100;
              const suggestedItem: Item | undefined = suggestedItems.find((si) => si.id === item.id);

              return (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-2xl border border-black/20 bg-[#fffaf5] p-4"
                  style={{
                    animation: "fadeUp 0.5s ease-out both",
                    animationDelay: `${120 + index * 60}ms`,
                  }}
                >
                  <div className="flex items-center gap-4">
                    <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-white shadow-sm">
                      <img src={suggestedItem?.imageURL} alt={suggestedItem?.name} className="h-10 w-10" />
                    </div>
                    <div>
                      <p className="text-base font-semibold text-black">
                        {suggestedItem?.name}
                      </p>
                      <p className="text-sm text-black/60">
                        ${price.toFixed(2)} × {item.quantity}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold text-black">
                      ${itemTotal.toFixed(2)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          <div
            className="space-y-3 rounded-2xl border border-black/20 bg-[#fffaf5] p-6"
            style={{
              animation: "fadeUp 0.7s ease-out both",
              animationDelay: "200ms",
            }}
          >
            <div className="flex justify-between text-base text-black/70">
              <span>Subtotal</span>
              <span className="font-mono">${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-base text-black/70">
              <span>Tax (8%)</span>
              <span className="font-mono">
                ${tax.toFixed(2)}
              </span>
            </div>
            <div className="border-t border-black/20 pt-3">
              <div className="flex justify-between">
                <span className="text-xl font-semibold text-black">Total</span>
                <span className="text-xl font-semibold text-black">
                  ${total.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          <div
            className="flex flex-col gap-3 sm:flex-row"
            style={{
              animation: "fadeUp 0.7s ease-out both",
              animationDelay: "260ms",
            }}
          >
            <button
              type="button"
              onClick={handlePlaceOrder}
              className="flex-1 rounded-2xl border border-black/30 bg-white py-3 text-sm font-semibold text-black/70 transition hover:border-black/50"
            >
              Place Order
            </button>
          </div>
        </div>
      </div>
    );
  }

  const itemCards = cartItems.length ? (
    <div className="space-y-3">
      {cartItems.map((item) => {
        const suggestedItem: Item | undefined = suggestedItems.find((it) => it.id === item.id);
        return (
          <div
            key={item.id}
            className="flex items-center justify-between rounded-2xl border border-black/20 bg-[#fffaf5] p-3"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-sm">
                <img src={suggestedItem?.imageURL} alt={suggestedItem?.name} className="h-8 w-8" />
              </div>
              <div>
                <p className="text-sm font-semibold text-black">{suggestedItem?.name}</p>
                <p className="text-xs text-black/60">
                  Qty <span className="font-mono">{item.quantity ?? 0}</span>
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => adjustQuantity(item.id, -1)}
                className="h-8 w-8 rounded-full border border-black/30 text-lg font-semibold text-black/70 transition hover:bg-white"
                aria-label={`Decrease ${suggestedItem?.name}`}
              >
                -
              </button>
              <button
                type="button"
                onClick={() => adjustQuantity(item.id, 1)}
                className="h-8 w-8 rounded-full border border-black/30 text-lg font-semibold text-black/70 transition hover:bg-white"
                aria-label={`Increase ${suggestedItem?.name}`}
              >
                +
              </button>
            </div>
          </div>
        )
      })}
    </div>
  ) : (
    <div className="rounded-2xl border border-dashed border-black/40 bg-[#fffaf5] p-6 text-center text-sm text-black/60">
      Your cart is empty. Add a few items to get started.
    </div>
  );

  return (
    <div
      className="min-h-screen w-full bg-white text-black bg-[radial-gradient(circle_at_top_left,_#fff7ed_0,_#ffffff_55%),radial-gradient(circle_at_bottom_right,_#eef2ff_0,_#ffffff_45%)]"
      style={{
        fontFamily: '"Trebuchet MS", "Gill Sans", "Lucida Grande", sans-serif',
      }}
      data-theme="light"
    >
      <style>{animationStyles}</style>
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-8 md:px-6 lg:px-8">
        <header
          className="space-y-2"
          style={{ animation: "fadeUp 0.6s ease-out both" }}
        >
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-black/60">
            Simple cart
          </p>
          <h1 className="text-2xl font-semibold tracking-tight">
            Pick a few essentials
          </h1>
          <p className="text-sm text-black/70">
            Update your cart through the chat or tap to add a suggestion or
            adjust quantities.
          </p>
        </header>

        <div
          className="grid gap-8 lg:grid-cols-[1.4fr_1fr]"
          style={{
            animation: "fadeUp 0.7s ease-out both",
            animationDelay: "80ms",
          }}
        >
          <section className="space-y-4">
            <header className="flex items-center justify-between">
              <p className="text-sm font-semibold uppercase tracking-widest text-black/70">
                Suggested items
              </p>
            </header>
            <div className="grid gap-4 sm:grid-cols-2">
              {suggestedItems.map(({ id, name, description, imageURL }, index) => (
                <div
                  key={name}
                  className="flex items-center justify-between gap-3 rounded-2xl border border-black/20 bg-[#fffaf5] p-4"
                  style={{
                    animation: "fadeUp 0.5s ease-out both",
                    animationDelay: `${120 + index * 80}ms`,
                  }}
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white shadow-sm">
                      {imageURL && <img src={imageURL} alt={name} className="h-10 w-10" />}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-black">
                        {name}
                      </p>
                      <p className="text-xs text-black/60">{description}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => addItem(id)}
                    className="rounded-full bg-amber-200 px-3 py-1.5 text-xs font-semibold text-black transition hover:bg-amber-300"
                  >
                    Add
                  </button>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-4">
            <header className="flex items-center justify-between">
              <p className="text-sm font-semibold uppercase tracking-widest text-black/70">
                Cart
              </p>
              <span className="text-xs text-black/60">
                {cartItems.length} items
              </span>
            </header>
            {itemCards}
            <button
              type="button"
              disabled={cartItems.length === 0}
              onClick={submitCheckout}
              className="w-full rounded-2xl border border-black/30 bg-white py-3 text-sm font-semibold text-black/70 transition hover:border-black/50 disabled:cursor-not-allowed disabled:opacity-70"
            >
              Check out
            </button>
          </section>
        </div>

        <section className="space-y-3">
          <header className="flex items-center justify-between">
            <p className="text-sm font-semibold uppercase tracking-widest text-black/70">
              Widget state & output
            </p>
            <span className="text-xs text-black/60">Debug view</span>
          </header>
          <div className="grid gap-4 lg:grid-cols-2">
            <JsonPanel label="window.openai.widgetState" value={cartState} />
            <JsonPanel label="window.openai.toolOutput" value={toolOutput} />
          </div>
        </section>
      </div>
    </div>
  );
}

const rootElement = document.getElementById("shopping-cart-root");
if (!rootElement) {
  throw new Error("Missing shopping-cart-root element");
}

createRoot(rootElement).render(<App />);
