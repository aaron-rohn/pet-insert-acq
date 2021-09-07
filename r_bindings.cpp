#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <type_traits>

#include <inttypes.h>
#include <Rcpp.h>

#define EV_SIZE 16
#define BYTE_IS_HEADER(byte) ( ((byte) >> 3) == 0x1F )
#define BLOCK_TO_MODULE(block) ((block) >> 2)

typedef struct event {
    uint16_t flag;    

    /*
    uint16_t A;
    uint16_t B;
    uint16_t C;
    uint16_t D;

    uint16_t E;
    uint16_t F;
    uint16_t G;
    uint16_t H;
    */

    uint16_t e1;
    uint16_t e2;

    double x;
    double y;

    uint16_t block;
    uint64_t time;
    uint64_t tt;
    uint64_t abs_time;
} Event;

bool operator<(const Event &ev1, const Event &ev2) {
    return ev1.abs_time < ev2.abs_time;
}

typedef struct coincidence {
    double x_a, y_a;
    uint16_t e_a1, e_a2;

    double x_b, y_b;
    uint16_t e_b1, e_b2;

    uint16_t block_a, block_b;
    int64_t tdiff;

    coincidence(Event &ev_a, Event &ev_b) 
    {
        e_a1 = ev_a.e1;
        e_a2 = ev_a.e2;
        x_a = ev_a.x;
        y_a = ev_a.y;

        e_b1 = ev_b.e1;
        e_b2 = ev_b.e2;
        x_b = ev_b.x;
        y_b = ev_b.y;

        block_a = ev_a.block;
        block_b = ev_b.block;
        tdiff = ev_a.abs_time - ev_b.abs_time;
    };
} Coincidence;

// [[Rcpp::export]]
Rcpp::DataFrame read_data (std::string filename, bool do_coincidences = false, uint64_t window = 100)
{
    FILE *file = fopen(filename.c_str(), "rb");
    uint8_t data[EV_SIZE] = {0};

    uint64_t file_length, file_elems;
    if (file) 
    {
        fseek(file, 0L, SEEK_END);
        file_length = ftell(file);
        rewind(file);

        file_elems = file_length / EV_SIZE;
        std::cout << "Found " << std::to_string(file_elems) << " entries" << std::endl;

        if (file_length % EV_SIZE != 0)
        {
            std::cout << "File length does not appear to be "
                "a multiple of the event size." << std::endl;
        }
    } 
    else 
    {
        throw std::runtime_error("Unable to open file.");
    }

    std::vector<Event> events;
    Event ev;

    std::vector<uint64_t> last_tt(16);
    std::vector<uint16_t> A_vec, B_vec, C_vec, D_vec;
    std::vector<uint16_t> E_vec, F_vec, G_vec, H_vec;

    int nread;

    while (fread(data, 1, EV_SIZE, file) == EV_SIZE)
    {
        if (!BYTE_IS_HEADER(data[0]))
        {
            bool synced = false;
            printf("Lost sync\n");

            // Look internally for the header
            for (int i = 1; i < EV_SIZE; i++)
            {
                if (BYTE_IS_HEADER(data[i]))
                {
                    memmove(data, data + i, EV_SIZE - i);

                    if (fread(data + (EV_SIZE - i), 1, i, file) != (size_t)i)
                        goto done_reading;

                    synced = true;
                }
            }

            // Read data until finding a valid header byte
            for (int i = 1; synced == false; i++)
            {
                if (fread(data, 1, 1, file) != 1) 
                    goto done_reading;

                if (BYTE_IS_HEADER(data[0]))
                {
                    if (fread(data + 1, 1, EV_SIZE-1, file) != (EV_SIZE-1)) 
                        goto done_reading;

                    synced = true;
                }
            }
        }

        // CRC | f |    b   |   E1   |    E2   |   E3    |   E4   |   E5    |   E6   |   E7    |   E8   |       TT
        // { 5 , 1 , 2 }{ 4 , 4 }{ 8 }{ 8 }{ 4 , 4 }{ 8 }{ 8 }{ 4 , 4 }{ 8 }{ 8 }{ 4 , 4 }{ 8 }{ 8 }{ 4 , 4 }{ 8 }{ 8 }
        //       0          1      2    3      4      5    6      7      8    9     10     11   12     13     14   15
        
        ev.flag  = (data[0] >> 2) & 0x1;
        ev.block = ((data[0] << 4)  | (data[1] >> 4)) & 0x3F;
        int mod = BLOCK_TO_MODULE(ev.block);

        if (ev.flag)
        {
            // Data is a single event

            uint16_t A = ((data[1]  << 8) | data[2])  & 0xFFF;
            uint16_t C = ((data[4]  << 8) | data[5])  & 0xFFF;
            uint16_t E = ((data[7]  << 8) | data[8])  & 0xFFF;
            uint16_t G = ((data[10] << 8) | data[11]) & 0xFFF;

            uint16_t B = (data[3]  << 4) | (data[4]  >> 4);
            uint16_t D = (data[6]  << 4) | (data[7]  >> 4);
            uint16_t F = (data[9]  << 4) | (data[10] >> 4);
            uint16_t H = (data[12] << 4) | (data[13] >> 4);

            ev.e1 = A + B + C + D;
            ev.e2 = E + F + G + H;

            double x1 = 1, x2 = 1, y1 = 1, y2 = 1;

            if (ev.e1 > 0) {
                x1 = (A + B) / ((double)ev.e1);
                y1 = (A + D) / ((double)ev.e1);
            }

            if (ev.e2 > 0) {
                x2 = (E + F) / ((double)ev.e2);
                y2 = (E + H) / ((double)ev.e2);
            }

            ev.x = x1;
            //ev.y = (y1 + y2) / 2;
            ev.y = y1;

            ev.time     = ((data[13] << 16) | (data[14] << 8) | data[15]) & 0xFFFFF;
            ev.tt       = last_tt[mod];
            ev.abs_time = (ev.tt * (100e-6 / 10e-9 * 8)) + ev.time;

            events.push_back(ev);

            if (!do_coincidences)
            {
                A_vec.push_back(A);
                B_vec.push_back(B);
                C_vec.push_back(C);
                D_vec.push_back(D);

                E_vec.push_back(E);
                F_vec.push_back(F);
                G_vec.push_back(G);
                H_vec.push_back(H);
            }
        }
        else
        {
            // Data is a time tag, so update counter for the appropriate module
            
            // CRC | f |    b   |                     0's                    |             TT
            // { 5 , 1 , 2 }{ 4 , 4 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }{ 8 }
            //       0          1      2    3    4    5    6    7    8    9   10   11   12   13   14   15
            uint64_t upper = (data[10] << 16) | (data[11] << 8) | data[12];
            uint64_t lower = (data[13] << 16) | (data[14] << 8) | data[15];
            last_tt[mod] = (upper << 24) | lower;
        }

    }

done_reading:

    fclose(file);

    if (do_coincidences)
    {
        std::sort(events.begin(), events.end()); 
        std::vector<Coincidence> coins;
        int sz = events.size();

        for (int i = 0; i < sz; i++) 
        {
            Event &ev1 = events[i];
            uint8_t m = BLOCK_TO_MODULE(ev1.block);

            for (int j = i + 1;
                 ((events[j].abs_time - ev1.abs_time) < window) && (j < sz); 
                 j++)
            {
                Event &ev2 = events[j];
                uint8_t this_m = BLOCK_TO_MODULE(ev2.block);

                if (m != this_m)
                {
                    Event &ev_a = (ev1.block < ev2.block) ? ev1 : ev2;
                    Event &ev_b = (ev1.block < ev2.block) ? ev2 : ev1;

                    coins.push_back(Coincidence (ev_a, ev_b));
                }
            }
        }

        // return the coincidence data
        std::vector<double> x_a, y_a, x_b, y_b;
        std::vector<uint16_t> e_a1, e_a2, e_b1, e_b2, block_a, block_b;
        std::vector<int64_t> tdiff;

        for (Coincidence &c : coins)
        {
            x_a.push_back(c.x_a);
            y_a.push_back(c.y_a);
            e_a1.push_back(c.e_a1);
            e_a2.push_back(c.e_a2);
            block_a.push_back(c.block_a);

            x_b.push_back(c.x_b);
            y_b.push_back(c.y_b);
            e_b1.push_back(c.e_b1);
            e_b2.push_back(c.e_b2);
            block_b.push_back(c.block_b);

            tdiff.push_back(c.tdiff);
        }

        return Rcpp::DataFrame::create(
                Rcpp::Named("x_a") = x_a,
                Rcpp::Named("y_a") = y_a,
                Rcpp::Named("e_a1") = e_a1,
                Rcpp::Named("e_a2") = e_a2,
                Rcpp::Named("block_a") = block_a,

                Rcpp::Named("x_b") = x_b,
                Rcpp::Named("y_b") = y_b,
                Rcpp::Named("e_b1") = e_b1,
                Rcpp::Named("e_b2") = e_b2,
                Rcpp::Named("block_b") = block_b,

                Rcpp::Named("tdiff") = tdiff
                );
    }
    else
    {
        // return the singles data
        
        std::vector<uint16_t> e1, e2, block;
        std::vector<double> x, y;
        std::vector<uint64_t> abs_time;

        for (Event &ev : events)
        {
            e1.push_back(ev.e1);
            e2.push_back(ev.e2);
            x.push_back(ev.x);
            y.push_back(ev.y);
            block.push_back(ev.block);
            abs_time.push_back(ev.abs_time);
        }

        return Rcpp::DataFrame::create(
                Rcpp::Named("e1") = e1,
                Rcpp::Named("e2") = e2,
                Rcpp::Named("x") = x,
                Rcpp::Named("y") = y,
                Rcpp::Named("block") = block,
                Rcpp::Named("abs_time") = abs_time
            /*
                Rcpp::Named("A") = A_vec,
                Rcpp::Named("B") = B_vec,
                Rcpp::Named("C") = C_vec,
                Rcpp::Named("D") = D_vec,
                Rcpp::Named("E") = E_vec,
                Rcpp::Named("F") = F_vec,
                Rcpp::Named("G") = G_vec,
                Rcpp::Named("H") = H_vec
             */
                );
    }
}
