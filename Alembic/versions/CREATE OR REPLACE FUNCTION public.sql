CREATE OR REPLACE FUNCTION public.update_suborder_snapshot()
RETURNS TRIGGER AS $$
DECLARE 
    snap_time TIMESTAMPTZ;
BEGIN
    IF NEW.status <> 'delivered' THEN
        RETURN NEW;
    END IF;

    snap_time := date_trunc('hour', NEW.created_at);

    INSERT INTO public.suborder_snapshots (
        store_id,
        snapshot_time,
        total_orders,
        total_revenue,
        total_customers
    )
    VALUES (
        NEW.store_id,
        snap_time,
        1,
        NEW.total_amount,
        1
    )
    ON CONFLICT (store_id, snapshot_time)
    DO UPDATE SET
        total_orders = suborder_snapshots.total_orders + 1,
        total_revenue = suborder_snapshots.total_revenue + NEW.total_amount,
        total_customers = suborder_snapshots.total_customers + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_suborder_snapshot
AFTER INSERT OR UPDATE OF status ON public.suborders
FOR EACH ROW
EXECUTE FUNCTION public.update_suborder_snapshot();