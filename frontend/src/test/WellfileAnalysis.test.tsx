import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WellfileAnalysis } from '../components/WellfileAnalysis';

const mockWell = {
    API_WellNo: '3000000000000',
    Lat: 47.5,
    Long: -105.2,
};

describe('WellfileAnalysis', () => {
    it('shows retry button and error message when error is true', () => {
        const onRetry = vi.fn();

        render(
            <WellfileAnalysis
                selectedWell={mockWell}
                loading={false}
                analysis={null}
                wellfileUrl={null}
                error={true}
                onRetry={onRetry}
            />
        );

        expect(screen.getByText(/could not load wellfile analysis/i)).toBeInTheDocument();
        expect(screen.getByText(/temporary issue.*try again/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /retry analysis/i })).toBeInTheDocument();
    });

    it('does not show retry button when error is false', () => {
        render(
            <WellfileAnalysis
                selectedWell={mockWell}
                loading={false}
                analysis={null}
                wellfileUrl={null}
                error={false}
                onRetry={vi.fn()}
            />
        );

        expect(screen.getByText(/no wellfile analysis available/i)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /retry analysis/i })).not.toBeInTheDocument();
    });

    it('shows the select-a-well prompt when no well is selected', () => {
        render(
            <WellfileAnalysis
                selectedWell={null}
                loading={false}
                analysis={null}
                wellfileUrl={null}
                error={false}
                onRetry={vi.fn()}
            />
        );

        expect(screen.getByText(/select a well from the map tab/i)).toBeInTheDocument();
    });

    it('shows loading spinner when loading and no analysis', () => {
        render(
            <WellfileAnalysis
                selectedWell={mockWell}
                loading={true}
                analysis={null}
                wellfileUrl={null}
                error={false}
                onRetry={vi.fn()}
            />
        );

        expect(screen.getByText(/analyzing wellfile data/i)).toBeInTheDocument();
    });

    it('renders analysis data when analysis is provided', () => {
        render(
            <WellfileAnalysis
                selectedWell={mockWell}
                loading={false}
                analysis={{
                    api_number: '3000000000000',
                    extraction_status: 'SUCCESS',
                    cache_hit: true,
                    well_name: 'TEST WELL 1',
                }}
                wellfileUrl={null}
                error={false}
                onRetry={vi.fn()}
            />
        );

        expect(screen.getByText(/wellfile analysis/i)).toBeInTheDocument();
        expect(screen.getByText(/test well 1/i)).toBeInTheDocument();
    });
});
