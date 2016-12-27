import numpy
import pyopencl as cl

from simple_gene import SimpleGene

class ShufflerChromosome:
    # ShufflerChromosome - a chromosome contains a list of Genes.
    # __genes - an ordered list of Genes
    # __name - name of the chromosome
    # dna - an listed of Gene's dna
    # dna_total_length - sum of the lenght of all genes's dna
    def __init__(self, genes, name=""):
        assert all(isinstance(gene, SimpleGene) for gene in genes)
        assert type(genes) == list
        self.__genes = genes
        self.__name = name

    @property
    def num_of_genes(self):
        return len(self.__genes)

    @property
    def name(self):
        return self.__name

    @property
    def dna_total_length(self):
        return self.num_of_genes

    @property
    def dna(self):
        return [gene.dna for gene in self.__genes]

    @dna.setter
    def dna(self, dna):
        assert self.num_of_genes == len(dna)
        for i, gene in enumerate(self.__genes):
            gene.dna = dna[i]

    @property
    def genes(self):
        return self.__genes

    @property
    def gene_elements(self):
        return [] if len(self.__genes) == 0 else self.__genes[0].elements

    @property
    def gene_elements_in_kernel(self):
        return [] if len(self.__genes) == 0 else self.__genes[0].elements_in_kernel

    @property
    def kernel_file(self):
        return "shuffler_chromosome.c"

    @property
    def struct_name(self):
        return "__ShufflerChromosome";

    @property
    def chromosome_size_define(self):
        return "SHUFFLER_CHROMOSOME_GENE_SIZE"

    def kernelize(self):
        candidates = self.__genes[0].kernelize()
        defines = "#define SHUFFLER_CHROMOSOME_GENE_SIZE " + str(self.num_of_genes) + "\n"
        return candidates + defines

    def preexecute_kernels(self, ctx, queue, population):
        ## initialize global variables for kernel execution
        survivors = numpy.zeros(population, dtype=numpy.bool)
        best_fit = [0]
        weakest_fit = [0]

        mf = cl.mem_flags

        self.__dev_best = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR,
                                    hostbuf=numpy.array(best_fit, dtype=numpy.float32))
        self.__dev_weakest = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR,
                                       hostbuf=numpy.array(weakest_fit, dtype=numpy.float32))
        self.__dev_survivors = cl.Buffer(ctx, mf.WRITE_ONLY, survivors.nbytes)

    def get_populate_kernel_names(self):
        return ["shuffler_chromosome_populate"]

    def get_crossover_kernel_names(self):
        return ["shuffler_chromosome_update_survivors",\
                "shuffler_chromosome_crossover"]

    def get_mutation_kernel_names(self):
        return ["shuffler_chromosome_mutate"]

    def execute_populate(self, prg, queue, population, dev_chromosomes, dev_rnum):
        prg.shuffler_chromosome_populate(queue,
                                         (population,),
                                         (1,),
                                         dev_chromosomes,
                                         dev_rnum).wait()

    def execute_crossover(self, prg, queue, population, generation_idx, prob_crossover,
                          dev_chromosomes, dev_fitnesses, dev_rnum):
        prg.shuffler_chromosome_update_survivors(queue,
                                                 (1,),
                                                 (1,),
                                                 dev_fitnesses,
                                                 self.__dev_best,
                                                 self.__dev_weakest,
                                                 self.__dev_survivors).wait()
        prg.shuffler_chromosome_crossover(queue,
                                          (population,),
                                          (1,),
                                          dev_chromosomes,
                                          dev_fitnesses,
                                          self.__dev_survivors,
                                          numpy.float32(prob_crossover),
                                          dev_rnum).wait()


    def execute_mutation(self, prg, queue, population, generation_idx, prob_mutate,
                         dev_chromosomes, dev_fitnesses, dev_rnum):
        prg.shuffler_chromosome_mutate(queue,
                                       (population,),
                                       (1,),
                                       dev_chromosomes,
                                       numpy.float32(prob_mutate),
                                       dev_rnum).wait()